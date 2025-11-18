import numpy as np

class Bandit:
    def __init__(self, d=5, actions=[1,2,3,4], lam=1.0, v=0.5):
        self.actions = actions
        self.d = d
        self.lam, self.v = lam, v
        self.A = {a: lam*np.eye(d) for a in actions}
        self.b = {a: np.zeros(d) for a in actions}
        self.last_action = None
        self.last_context = None

    def pick_action(self, x):
        best, best_val = None, -1e9
        for a in self.actions:
            Ainv = np.linalg.inv(self.A[a])
            mu = Ainv @ self.b[a]
            theta = np.random.multivariate_normal(mu, self.v**2 * Ainv)
            val = x @ theta
            if val > best_val:
                best, best_val = a, val
        self.last_action, self.last_context = best, x
        return best

    def update(self, a, x, r):
        self.A[a] += np.outer(x, x)
        self.b[a] += r * x
