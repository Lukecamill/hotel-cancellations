import numpy as np
import pandas as pd
import pytest
from hotel_cancel.contracts import RAW_COLUMNS, validate_raw, DataContractError




def test_contract_accepts_valid_input_without_mutating_it(valid_raw):
    before=valid_raw.copy(deep=True)
    assert validate_raw(valid_raw)['errors']==[]
    pd.testing.assert_frame_equal(valid_raw,before)


@pytest.mark.parametrize('column,value', [('is_canceled',2),('is_canceled',1),('lead_time',-1),
    ('adults',1.5),('adr',np.inf),('adr',np.nan),('hotel','Other Hotel'),
    ('arrival_date_month','Bad'),('arrival_date_day_of_month',30),('arrival_date_year',2018),
    ('arrival_date_week_number',54),('reservation_status_date','bad'),('meal',''),('lead_time','7')])
def test_contract_rejects_invalid_rows(valid_raw,column,value):
    valid_raw[column]=value
    with pytest.raises(DataContractError):validate_raw(valid_raw)


def test_contract_rejects_missing_extra_duplicate_columns_and_empty_input(valid_raw):
    for bad in [valid_raw.drop(columns='adr'),valid_raw.assign(new_field=1),
                pd.concat([valid_raw,valid_raw[['adr']]],axis=1),valid_raw.iloc[:0]]:
        with pytest.raises(DataContractError):validate_raw(bad)


def test_known_anomalies_are_counted_not_silently_removed(valid_raw):
    df=pd.concat([valid_raw]*3,ignore_index=True)
    df['adr']=[-6.38,0.,5400.];df['children']=np.nan;df['country']=[None,'CN','PRT']
    df['adults']=0;df['stays_in_week_nights']=0;df['market_segment']='Undefined'
    before=df.copy(deep=True);report=validate_raw(df)
    assert report['rows']==3
    assert report['anomalies']['negative_adr']==1
    assert report['anomalies']['zero_guests']==3
    assert report['anomalies']['zero_nights']==3
    assert report['anomalies']['non_alpha3_country']==1
    pd.testing.assert_frame_equal(df,before)
