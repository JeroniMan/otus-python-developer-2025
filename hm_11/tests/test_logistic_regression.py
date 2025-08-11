# tests/test_logistic_regression.py
import numpy as np
import pytest
from scipy import sparse
from dmia.classifiers.logistic_regression import LogisticRegression


class TestLogisticRegression:
    """Test suite for LogisticRegression class."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        np.random.seed(42)
        n_samples, n_features = 100, 20
        X = np.random.randn(n_samples, n_features)
        # Create linearly separable data
        w_true = np.random.randn(n_features)
        y = (X.dot(w_true) + np.random.randn(n_samples) * 0.1 > 0).astype(int)
        return sparse.csr_matrix(X), y

    @pytest.fixture
    def trained_model(self, sample_data):
        """Create and train a model."""
        X, y = sample_data
        model = LogisticRegression()
        model.train(X, y, learning_rate=0.1, num_iters=100, batch_size=20, verbose=False)
        return model

    def test_initialization(self):
        """Test model initialization."""
        model = LogisticRegression()
        assert model.w is None
        assert model.loss_history is None

    def test_append_biases(self, sample_data):
        """Test bias appending to feature matrix."""
        X, _ = sample_data
        X_with_bias = LogisticRegression.append_biases(X)

        assert X_with_bias.shape[0] == X.shape[0]
        assert X_with_bias.shape[1] == X.shape[1] + 1
        # Check that last column is all ones
        assert np.allclose(X_with_bias[:, -1].toarray().flatten(), 1)

    def test_train_initializes_weights(self, sample_data):
        """Test that training initializes weights properly."""
        X, y = sample_data
        model = LogisticRegression()
        model.train(X, y, num_iters=10, verbose=False)

        assert model.w is not None
        assert model.w.shape == (X.shape[1] + 1,)  # +1 for bias
        assert model.loss_history is not None
        assert len(model.loss_history) == 10

    def test_loss_decreases(self, sample_data):
        """Test that loss generally decreases during training."""
        X, y = sample_data
        model = LogisticRegression()
        model.train(X, y, learning_rate=0.1, num_iters=100, verbose=False)

        # Check that loss decreases on average
        losses = model.loss_history
        avg_early = np.mean(losses[:20])
        avg_late = np.mean(losses[-20:])
        assert avg_late < avg_early

    def test_predict_proba_shape(self, sample_data, trained_model):
        """Test predict_proba output shape."""
        X, _ = sample_data
        proba = trained_model.predict_proba(X, append_bias=True)

        assert proba.shape == (X.shape[0], 2)
        # Check that probabilities sum to 1
        assert np.allclose(proba.sum(axis=1), 1.0)
        # Check that all probabilities are between 0 and 1
        assert np.all(proba >= 0) and np.all(proba <= 1)

    def test_predict_output(self, sample_data, trained_model):
        """Test predict output."""
        X, _ = sample_data
        predictions = trained_model.predict(X)

        assert predictions.shape == (X.shape[0],)
        assert set(predictions).issubset({0, 1})

    def test_activated_func(self, trained_model):
        """Test sigmoid activation function."""
        # Test known values
        assert np.isclose(trained_model.activated_func(0), 0.5)
        assert trained_model.activated_func(100) > 0.99
        assert trained_model.activated_func(-100) < 0.01

        # Test that it's monotonic
        x = np.linspace(-10, 10, 100)
        y = trained_model.activated_func(x)
        assert np.all(np.diff(y) > 0)

    def test_loss_with_regularization(self, sample_data):
        """Test that regularization affects the loss."""
        X, y = sample_data
        model = LogisticRegression()

        # Train with different regularization strengths
        model.train(X, y, reg=0.0, num_iters=50, verbose=False)
        loss_no_reg = model.loss_history[-1]

        model.w = None  # Reset model
        model.train(X, y, reg=1.0, num_iters=50, verbose=False)
        loss_with_reg = model.loss_history[-1]

        # With regularization, final loss might be higher due to penalty
        assert loss_with_reg != loss_no_reg

    @pytest.mark.parametrize("batch_size", [10, 50, 100])
    def test_different_batch_sizes(self, sample_data, batch_size):
        """Test training with different batch sizes."""
        X, y = sample_data
        model = LogisticRegression()
        model.train(X, y, batch_size=batch_size, num_iters=50, verbose=False)

        assert model.w is not None
        assert len(model.loss_history) == 50

    def test_convergence_on_simple_data(self):
        """Test that the model converges on linearly separable data."""
        np.random.seed(42)
        # Create perfectly separable data
        X = np.array([[1, 1], [1, 2], [2, 1], [5, 5], [5, 6], [6, 5]])
        y = np.array([0, 0, 0, 1, 1, 1])
        X_sparse = sparse.csr_matrix(X)

        model = LogisticRegression()
        model.train(X_sparse, y, learning_rate=0.5, num_iters=1000, verbose=False)

        predictions = model.predict(X_sparse)
        accuracy = np.mean(predictions == y)
        assert accuracy > 0.8  # Should achieve good accuracy on separable data


# tests/test_gradient_check.py
import numpy as np
import pytest
from dmia.gradient_check import eval_numerical_gradient, grad_check_sparse


class TestGradientCheck:
    """Test suite for gradient checking utilities."""

    def test_eval_numerical_gradient_linear(self):
        """Test numerical gradient on a linear function."""

        # f(x) = 2*x[0] + 3*x[1]
        def linear_func(x):
            return 2 * x[0] + 3 * x[1]

        x = np.array([1.0, 2.0])
        grad = eval_numerical_gradient(linear_func, x)

        # Analytical gradient should be [2, 3]
        assert np.allclose(grad, [2.0, 3.0], atol=1e-4)

    def test_eval_numerical_gradient_quadratic(self):
        """Test numerical gradient on a quadratic function."""

        # f(x) = x[0]^2 + 2*x[1]^2
        def quadratic_func(x):
            return x[0] ** 2 + 2 * x[1] ** 2

        x = np.array([3.0, 4.0])
        grad = eval_numerical_gradient(quadratic_func, x)

        # Analytical gradient should be [2*x[0], 4*x[1]] = [6, 16]
        assert np.allclose(grad, [6.0, 16.0], atol=1e-4)

    def test_grad_check_sparse(self, capsys):
        """Test sparse gradient checking."""

        # f(x) = sum(x^2)
        def sum_squares(x):
            return np.sum(x ** 2)

        x = np.random.randn(10)
        analytic_grad = 2 * x  # Gradient of sum(x^2)

        grad_check_sparse(sum_squares, x, analytic_grad, num_checks=5)

        # Check that output was printed
        captured = capsys.readouterr()
        assert "numerical:" in captured.out
        assert "analytic:" in captured.out
        assert "relative error:" in captured.out

    def test_gradient_check_consistency(self):
        """Test that gradient check gives consistent results."""
        np.random.seed(42)

        def complex_func(x):
            return np.sum(np.sin(x) + x ** 2)

        x = np.random.randn(5)
        grad1 = eval_numerical_gradient(complex_func, x)
        grad2 = eval_numerical_gradient(complex_func, x)

        # Should get the same gradient for the same input
        assert np.allclose(grad1, grad2)


# tests/test_utils.py
import numpy as np
import matplotlib.pyplot as plt
import pytest
from unittest.mock import patch, MagicMock
from utils import plot_surface


class TestUtils:
    """Test suite for utility functions."""

    @patch('matplotlib.pyplot.figure')
    @patch('matplotlib.pyplot.pcolormesh')
    @patch('matplotlib.pyplot.scatter')
    def test_plot_surface(self, mock_scatter, mock_pcolormesh, mock_figure):
        """Test plot_surface function."""
        # Create mock classifier
        mock_clf = MagicMock()
        mock_clf.predict = MagicMock(return_value=np.array([0, 1, 0, 1]))

        # Create sample data
        X = np.array([[1, 2], [3, 4], [5, 6], [7, 8]])
        y = np.array([0, 1, 0, 1])

        # Call the function
        plot_surface(X, y, mock_clf)

        # Check that plotting functions were called
        assert mock_figure.called
        assert mock_pcolormesh.called
        assert mock_scatter.called

    @pytest.mark.skip(reason="Requires display")
    def test_plot_surface_integration(self):
        """Integration test for plot_surface (skipped in CI)."""
        from dmia.classifiers.logistic_regression import LogisticRegression
        from scipy import sparse

        # Create simple 2D data
        X = np.array([[1, 1], [2, 2], [3, 1], [4, 2]])
        y = np.array([0, 0, 1, 1])

        # Train a simple model
        model = LogisticRegression()
        model.train(sparse.csr_matrix(X), y, num_iters=100, verbose=False)

        # This should not raise an error
        plot_surface(X, y, model)
        plt.close('all')  # Clean up