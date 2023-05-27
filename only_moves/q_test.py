from only_moves.q_values import Q90


def dixon_test(data, left=True, right=True, q_dict=Q90):
    """
    Keyword arguments:
        data = A ordered or unordered list of data points (int or float).
        left = Q-test of minimum value in the ordered list if True.
        right = Q-test of maximum value in the ordered list if True.
        q_dict = A dictionary of Q-values for a given confidence level,
            where the dict. keys are sample sizes N, and the associated values
            are the corresponding critical Q values. E.g.,
            {3: 0.97, 4: 0.829, 5: 0.71, 6: 0.625, ...}

    Returns a list of 2 values for the outliers, or None.
    E.g.,
       for [1,1,1] -> [None, None]
       for [5,1,1] -> [None, 5]
       for [5,1,5] -> [1, None]

    """
    assert (
        left or right
    ), "At least one of the variables, `left` or `right`, must be True."
    assert len(data) >= 3, "At least 3 data points are required"
    assert len(data) <= max(q_dict.keys()), "Sample size too large"

    sdata = sorted(data)
    Q_mindiff, Q_maxdiff = (0, 0), (0, 0)

    if left:
        Q_min = sdata[1] - sdata[0]
        try:
            Q_min /= sdata[-1] - sdata[0]
        except ZeroDivisionError:
            pass
        Q_mindiff = (Q_min - q_dict[len(data)], sdata[0])

    if right:
        Q_max = abs((sdata[-2] - sdata[-1]))
        try:
            Q_max /= abs((sdata[0] - sdata[-1]))
        except ZeroDivisionError:
            pass
        Q_maxdiff = (Q_max - q_dict[len(data)], sdata[-1])

    if not Q_mindiff[0] > 0 and not Q_maxdiff[0] > 0:
        outliers = (None, None)

    elif Q_mindiff[0] == Q_maxdiff[0]:
        outliers = (Q_mindiff[1], Q_maxdiff[1])

    elif Q_mindiff[0] > Q_maxdiff[0]:
        outliers = (Q_mindiff[1], None)

    else:
        outliers = (None, Q_maxdiff[1])

    return outliers
