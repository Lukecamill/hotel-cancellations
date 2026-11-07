"""Analytical checks of correlated releases and the operating point."""
import numpy as np
from hotel_cancel.policy import released_distribution, oversell


def test_two_room_block_cannot_release_only_one_room():
    np.testing.assert_allclose(released_distribution(np.array([0.25]), np.array([2])), [.75, 0, .25])


def test_independent_rooms_have_partial_release_probability():
    np.testing.assert_allclose(released_distribution(np.array([.5, .5]), np.array([1, 1])), [.25, .5, .25])


def test_walk_cost_changes_optimal_quantity_and_ties_choose_smallest():
    dist = np.array([.2, .3, .5])
    assert oversell(dist, 100, 400) == 0
    assert oversell(dist, 100, 100) == 1
    assert oversell(dist, 400, 100) == 2


def test_nightly_median_is_not_global_mean_and_negative_value_is_floored():
    import pandas as pd
    from hotel_cancel.policy import night_room_value
    assert night_room_value(pd.DataFrame({'adr':[100.,110.,5400.]}),20)==90.
    assert night_room_value(pd.DataFrame({'adr':[-6.38,0.,10.]}),20)==0.
    assert night_room_value(pd.DataFrame({'adr':[180.,190.,200.]}),20)==170.


def test_calibration_must_match_decision_horizon():
    import pandas as pd
    import pytest
    from sklearn.linear_model import LogisticRegression
    from hotel_cancel.policy import HorizonCalibrator, logit
    p=pd.Series([.1,.2,.8,.9]);labels=[0,1,0,1]
    model=LogisticRegression().fit(logit(p).to_frame('z'),labels)
    calibrated=HorizonCalibrator(7,model)
    np.testing.assert_array_equal(calibrated.predict(p,lead_days=7),model.predict_proba(logit(p).to_frame('z'))[:,1])
    with pytest.raises(ValueError):calibrated.predict(p,lead_days=0)


def test_policy_rejects_untagged_booking_probabilities_or_wrong_horizon():
    import pandas as pd
    import pytest
    from hotel_cancel.policy import run_policies, PolicyForecast
    nights=pd.DataFrame({'hotel':['City Hotel'],'arrival':pd.to_datetime(['2017-01-01']),
                         'block':[0],'y':[0],'p_cal':[.1]})
    aggregation={'p':('p_cal','mean'),'n':('p_cal','size')}
    for value in [(np.array([.9]),None),PolicyForecast(np.array([.1]),None,0)]:
        with pytest.raises(ValueError):
            run_policies(nights,{'bad':lambda g,b:value},lambda g:100.,block_agg=aggregation,walk_cost=250.,decision_lead_days=7)


import pytest


@pytest.mark.parametrize('probabilities,sizes',[(np.array([np.nan]),None),(np.array([1.1]),None),
    (np.array([-.1]),None),(np.array([.1,.2]),None),(np.array([.1]),np.array([2])),
    (np.array([.1]),np.array([0]))])
def test_invalid_policy_probabilities_and_block_counts_fail(probabilities,sizes):
    import pandas as pd
    from hotel_cancel.policy import run_policies, PolicyForecast
    frame=pd.DataFrame({'hotel':['City Hotel'],'arrival':pd.to_datetime(['2017-01-01']),
                        'block':[0],'y':[0],'p_cal':[.1]})
    with pytest.raises(ValueError):
        run_policies(frame,{'bad':lambda g,b:PolicyForecast(probabilities,sizes,7)},lambda g:100.,
                     block_agg={'p':('p_cal','mean'),'n':('p_cal','size')},walk_cost=250.,decision_lead_days=7)
