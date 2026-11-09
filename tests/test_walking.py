import numpy as np
import pandas as pd
import pytest

from hotel_cancel.walking import select_units,attribute,group_summary


@pytest.fixture
def units():
    return pd.DataFrame({'unit_id':['old','middle','new'],
                         'booked':pd.to_datetime(['2016-12-01','2016-12-20','2016-12-30'])})


def test_latest_booking_rule_and_seeded_lottery_are_reproducible(units):
    assert select_units(units,2,rule='latest_booking_first',seed=3217,night_key='City|2017-01-01')==['new','middle']
    first=select_units(units,2,rule='seeded_lottery',seed=3217,night_key='City|2017-01-01')
    shuffled=select_units(units.iloc[::-1],2,rule='seeded_lottery',seed=3217,night_key='City|2017-01-01')
    assert first==shuffled and len(set(first))==2
    assert select_units(units,0,rule='seeded_lottery',seed=3217,night_key='City|2017-01-01')==[]


@pytest.mark.parametrize('column',['country','nationality_source_code','market_segment','distribution_channel','adr','p_cal','is_canceled'])
def test_ranking_contract_rejects_sensitive_proxy_score_and_outcome_fields(units,column):
    with pytest.raises(ValueError,match='audit attributes'):
        select_units(units.assign(**{column:'not allowed'}),1,rule='latest_booking_first',seed=1,night_key='night')


@pytest.mark.parametrize('count',[-1,4,1.5,True])
def test_invalid_counts_cannot_silently_truncate_or_repeat_units(units,count):
    with pytest.raises(ValueError):select_units(units,count,rule='seeded_lottery',seed=1,night_key='night')


def test_missing_dates_and_duplicate_identifiers_fail(units):
    changed=units.copy();changed.loc[0,'booked']=pd.NaT
    with pytest.raises(ValueError,match='Missing'):select_units(changed,1,rule='latest_booking_first',seed=1,night_key='night')
    changed=units.copy();changed.loc[0,'unit_id']='new'
    with pytest.raises(ValueError,match='unique'):select_units(changed,1,rule='seeded_lottery',seed=1,night_key='night')


def fixture_nights():
    return pd.DataFrame(dict(unit_id=['old','new','cancelled','quiet'],hotel=['City Hotel']*4,
        arrival=pd.to_datetime(['2017-01-01']*3+['2017-01-02']),
        booked=pd.to_datetime(['2016-11-01','2016-12-20','2016-12-30','2016-12-01']),
        y=[0,0,1,0],market_segment=['Direct','Groups','Groups','Direct'],
        distribution_channel=['Direct','TA/TO','TA/TO','Direct'],nationality_source_code=['PRT','GBR','GBR','PRT']))


def test_attribution_selects_only_survivors_and_conserves_policy_overflow():
    nights=fixture_nights()
    decisions=pd.DataFrame(dict(hotel=['City Hotel']*2,night=pd.to_datetime(['2017-01-01','2017-01-02']),walked=[1,0]))
    allocations=attribute(nights,decisions,rule='latest_booking_first',seed=1)
    assert set(allocations.unit_id)=={'old','new','quiet'}
    assert allocations.loc[allocations.walked.eq(1),'unit_id'].tolist()==['new']
    assert allocations.uniform_expected_walks.sum()==pytest.approx(1.)
    assert allocations.walked.sum()==1
    changed=nights.copy()
    for c in ['nationality_source_code','market_segment','distribution_channel']:
        changed[c]=changed[c].iloc[::-1].to_numpy()
    altered=attribute(changed,decisions,rule='latest_booking_first',seed=1)
    assert allocations.unit_id.tolist()==altered.unit_id.tolist()
    assert allocations.walked.tolist()==altered.walked.tolist()


def test_insufficient_survivors_does_not_invent_guest_attributes():
    nights=fixture_nights()
    decisions=pd.DataFrame(dict(hotel=['City Hotel'],night=pd.to_datetime(['2017-01-01']),walked=[3]))
    with pytest.raises(ValueError,match='survivors'):attribute(nights,decisions,rule='latest_booking_first',seed=1)


def test_summary_distinguishes_nightly_exposure_from_pooled_disparity():
    data=pd.DataFrame(dict(hotel=['City Hotel']*4,rule=['seeded_lottery']*4,
             market_segment=['A','A','B','B'],distribution_channel=['A','A','B','B'],
             nationality_source_code=['A','A','B','B'],walked=[1,0,0,0],
             uniform_expected_walks=[.5,.5,0.,0.],walk_night=[True,True,False,False]))
    summary=group_summary(data,minimum=1,walk_cost=250)
    a=summary[(summary.dimension=='market_segment')&(summary.category=='A')].iloc[0]
    b=summary[(summary.dimension=='market_segment')&(summary.category=='B')].iloc[0]
    assert a.walking_rate==.5 and b.walking_rate==0
    assert a.actual_to_nightly_uniform_ratio==1
    assert pd.isna(b.actual_to_nightly_uniform_ratio)
    assert a.hotel_relocation_cost_eur==250
    suppressed=group_summary(data,minimum=30,walk_cost=250)
    assert not suppressed.reportable.any() and suppressed.walked.isna().all()


def test_attribution_rejects_duplicate_nights_and_fractional_overflow():
    nights=fixture_nights()
    decision=pd.DataFrame(dict(hotel=['City Hotel'],night=pd.to_datetime(['2017-01-01']),walked=[1.5]))
    with pytest.raises(ValueError,match='integer'):attribute(nights,decision,rule='latest_booking_first',seed=1)
    decision['walked']=1
    with pytest.raises(ValueError,match='unique'):attribute(nights,pd.concat([decision,decision]),rule='latest_booking_first',seed=1)
