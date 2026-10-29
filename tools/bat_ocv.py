"""Normalized OCV curve g(SOC) of models/BATTERY_beh.lib: monotone cubic
(PCHIP, Fritsch-Carlson) interpolation through the table points, so the
curve and its slope are continuous (a piecewise-linear table stalls the
LTspice time-step control when the SOC creeps across a breakpoint).

    python3 tools/bat_ocv.py      # prints the B-source expression for the .lib
"""
G_S = [0, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, .95, 1]
G_V = [0, .18, .30, .43, .51, .57, .62, .67, .72, .78, .87, .93, 1]


def _slopes(x, y):
    n = len(x)
    h = [x[k + 1] - x[k] for k in range(n - 1)]
    d = [(y[k + 1] - y[k]) / h[k] for k in range(n - 1)]
    m = [0.0] * n
    for k in range(1, n - 1):
        if d[k - 1] * d[k] <= 0:
            m[k] = 0.0
        else:  # weighted harmonic mean (Fritsch-Carlson / PCHIP)
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])

    def end(h0, h1, d0, d1):
        s = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
        if s * d0 <= 0:
            return 0.0
        if d0 * d1 <= 0 and abs(s) > abs(3 * d0):
            return 3 * d0
        return s
    m[0] = end(h[0], h[1], d[0], d[1])
    m[-1] = end(h[-1], h[-2], d[-1], d[-2])
    return m


SLOPES = _slopes(G_S, G_V)


def coeffs():
    """Per segment k: (x_k, a, b, c, e) with g = a + b*u + c*u^2 + e*u^3, u = s - x_k."""
    out = []
    for k in range(len(G_S) - 1):
        h = G_S[k + 1] - G_S[k]
        y0, y1, m0, m1 = G_V[k], G_V[k + 1], SLOPES[k], SLOPES[k + 1]
        c = (3 * (y1 - y0) / h - 2 * m0 - m1) / h
        e = (m0 + m1 - 2 * (y1 - y0) / h) / h ** 2
        out.append((G_S[k], y0, m0, c, e))
    return out


def g(s):
    s = min(max(s, 0.0), 1.0)
    for x0, a, b, c, e in reversed(coeffs()):
        if s >= x0:
            u = s - x0
            return a + u * (b + u * (c + u * e))
    return 0.0


def spice_expr(var="V(s,N)"):
    """Nested if() B-source expression; `var` is the clamped SOC expression."""
    cs = coeffs()
    expr = ""
    for k, (x0, a, b, c, e) in enumerate(cs):
        u = f"(x-{x0:g})"
        a, b, c, e = (0.0 if abs(v) < 1e-9 else v for v in (a, b, c, e))
        # full precision: a 1e-7 step at a segment joint is enough to stall the
        # time-step control when the SOC creeps across it
        poly = f"{a:.17g}+{u}*({b:.17g}+{u}*({c:.17g}+{u}*({e:.17g})))"
        if k < len(cs) - 1:
            expr += f"if(x<{cs[k + 1][0]:g}, {poly}, "
        else:
            expr += poly + ")" * (len(cs) - 1)
    return expr.replace("x", var)


if __name__ == "__main__":
    print(spice_expr("X"))
    print([round(m, 4) for m in SLOPES])
