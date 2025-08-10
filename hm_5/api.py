#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import hashlib
import json
import logging
import uuid
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, HTTPServer

import scoring
from store import Store

# Constants
SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class ValidationError(Exception):
    pass


class Field:
    """Base field descriptor for validation."""

    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def validate(self, value):
        if value is None and self.required:
            raise ValidationError(f"{self.name} is required")
        if value == "" and not self.nullable:
            raise ValidationError(f"{self.name} cannot be empty")


class CharField(Field):
    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, str):
            raise ValidationError(f"{self.name} must be a string")


class ArgumentsField(Field):
    def validate(self, value):
        super().validate(value)
        if value is not None and not isinstance(value, dict):
            raise ValidationError(f"{self.name} must be a dict")


class EmailField(CharField):
    def validate(self, value):
        super().validate(value)
        if value and "@" not in value:
            raise ValidationError(f"{self.name} must contain @")


class PhoneField(Field):
    def validate(self, value):
        super().validate(value)
        if value in (None, ""):
            return
        phone = str(value)
        if not (len(phone) == 11 and phone.isdigit() and phone.startswith("7")):
            raise ValidationError(f"{self.name} must be 11 digits starting with 7")


class DateField(Field):
    def validate(self, value):
        super().validate(value)
        if value in (None, ""):
            return
        try:
            datetime.datetime.strptime(value, "%d.%m.%Y")
        except (ValueError, TypeError):
            raise ValidationError(f"{self.name} must be in DD.MM.YYYY format")


class BirthDayField(DateField):
    def validate(self, value):
        super().validate(value)
        if value in (None, ""):
            return
        bd = datetime.datetime.strptime(value, "%d.%m.%Y")
        if (datetime.datetime.now() - bd).days > 70 * 365:
            raise ValidationError(f"{self.name} must be less than 70 years ago")


class GenderField(Field):
    def validate(self, value):
        super().validate(value)
        if value not in (None, "", 0, 1, 2):
            raise ValidationError(f"{self.name} must be 0, 1 or 2")


class ClientIDsField(Field):
    def validate(self, value):
        super().validate(value)
        if not value:
            if self.required:
                raise ValidationError(f"{self.name} is required")
            return
        if not isinstance(value, list) or not all(isinstance(i, int) for i in value):
            raise ValidationError(f"{self.name} must be a list of integers")


class RequestMeta(type):
    """Metaclass to collect fields."""

    def __new__(mcs, name, bases, namespace):
        fields = {}
        for key, value in namespace.items():
            if isinstance(value, Field):
                fields[key] = value
        namespace["_fields"] = fields
        return super().__new__(mcs, name, bases, namespace)


class Request(metaclass=RequestMeta):
    """Base request class."""

    def __init__(self, data=None):
        self._data = data or {}
        self._errors = []

    def validate(self):
        for name, field in self._fields.items():
            try:
                value = self._data.get(name)
                field.validate(value)
                setattr(self, name, value)
            except ValidationError as e:
                self._errors.append(str(e))
        return not self._errors


class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def validate(self):
        if not super().validate():
            return False

        # Check for required pairs
        pairs = [
            (self.phone, self.email),
            (self.first_name, self.last_name),
            (self.gender, self.birthday),
        ]

        if not any(all(v not in (None, "") for v in pair) for pair in pairs):
            self._errors.append(
                "At least one pair must be non-empty: phone-email, first_name-last_name, or gender-birthday"
            )
            return False

        return True


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode("utf-8")).hexdigest()
    else:
        digest = hashlib.sha512((request.account + request.login + SALT).encode("utf-8")).hexdigest()
    return digest == request.token


def online_score_handler(request, ctx, store):
    score_request = OnlineScoreRequest(request["body"]["arguments"])
    if not score_request.validate():
        return "; ".join(score_request._errors), INVALID_REQUEST

    # Update context with non-empty fields
    ctx["has"] = [k for k, v in score_request._data.items() if v not in (None, "") and k in score_request._fields]

    if request["body"].get("login") == ADMIN_LOGIN:
        return {"score": 42}, OK

    # Convert birthday string to datetime if present
    birthday = None
    if score_request.birthday:
        birthday = datetime.datetime.strptime(score_request.birthday, "%d.%m.%Y")

    score = scoring.get_score(
        store,
        score_request.phone,
        score_request.email,
        birthday,
        score_request.gender,
        score_request.first_name,
        score_request.last_name,
    )
    return {"score": score}, OK


def clients_interests_handler(request, ctx, store):
    interests_request = ClientsInterestsRequest(request["body"]["arguments"])
    if not interests_request.validate():
        return "; ".join(interests_request._errors), INVALID_REQUEST

    ctx["nclients"] = len(interests_request.client_ids)

    response = {}
    for client_id in interests_request.client_ids:
        try:
            interests = scoring.get_interests(store, str(client_id))
            response[str(client_id)] = interests
        except Exception as e:
            logging.error(f"Failed to get interests for client {client_id}: {e}")
            return "Storage unavailable", INTERNAL_ERROR

    return response, OK


def method_handler(request, ctx, store):
    handlers = {"online_score": online_score_handler, "clients_interests": clients_interests_handler}

    method_request = MethodRequest(request.get("body", {}))
    if not method_request.validate():
        return "; ".join(method_request._errors), INVALID_REQUEST

    if not check_auth(method_request):
        return "Forbidden", FORBIDDEN

    handler = handlers.get(method_request.method)
    if not handler:
        return "Method not found", NOT_FOUND

    return handler(request, ctx, store)


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {"method": method_handler}
    store = Store()

    def get_request_id(self, headers):
        return headers.get("HTTP_X_REQUEST_ID", uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers["Content-Length"]))
            request = json.loads(data_string)
        except (KeyError, ValueError, TypeError):
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode("utf-8"))
        return


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", action="store", type=int, default=8080)
    parser.add_argument("-l", "--log", action="store", default=None)
    args = parser.parse_args()
    logging.basicConfig(
        filename=args.log,
        level=logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )
    server = HTTPServer(("localhost", args.port), MainHTTPHandler)
    logging.info("Starting server at %s" % args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
