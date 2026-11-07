import pandas as pd
import pytest
from hotel_cancel.history import reconstruct_as_of


def test_asof_excludes_later_entries_and_earlier_cancellations_includes_same_day_cancellation():
    # Decision 8 August: before/at/after booking and cancellation boundaries.
    bk=pd.DataFrame({'arrival':pd.to_datetime(['2017-08-15']*7),
                     'booked':pd.to_datetime(['2017-08-01']*5+['2017-08-08','2017-08-09'])})
    out=pd.DataFrame({'is_canceled':[0,1,1,1,1,0,0],
                      'status_date':pd.to_datetime(['2017-08-16','2017-08-07','2017-08-08','2017-08-10','2017-08-15','2017-08-16','2017-08-16'])})
    _,live,late=reconstruct_as_of(bk,out,7)
    assert live.tolist()==[True,False,True,True,True,False,False]
    assert late[live].tolist()==[0,1,1,1]
    # An outcome changing after the cutoff does not change historical membership.
    out.loc[3,'status_date']=pd.Timestamp('2017-08-14')
    assert reconstruct_as_of(bk,out,7)[1].equals(live)


@pytest.mark.parametrize('horizon',[0,7,14])
def test_asof_lead_time_uses_requested_horizon(horizon):
    bk=pd.DataFrame({'arrival':pd.to_datetime(['2017-08-15']),'booked':pd.to_datetime(['2017-08-01'])})
    out=pd.DataFrame({'is_canceled':[1],'status_date':pd.to_datetime(['2017-08-15'])})
    day,live,late=reconstruct_as_of(bk,out,horizon)
    assert day.iloc[0]==pd.Timestamp('2017-08-15')-pd.Timedelta(days=horizon)
    assert bool(live.iloc[0])==(horizon<14)
    assert late.iloc[0]==1


def test_asof_rejects_misaligned_rows_and_invalid_horizon():
    bk=pd.DataFrame({'arrival':pd.to_datetime(['2017-08-15']),'booked':pd.to_datetime(['2017-08-01'])})
    out=pd.DataFrame({'is_canceled':[0],'status_date':pd.to_datetime(['2017-08-16'])},index=[1])
    with pytest.raises(ValueError):reconstruct_as_of(bk,out,7)
    with pytest.raises(ValueError):reconstruct_as_of(bk,out.reset_index(drop=True),15)
