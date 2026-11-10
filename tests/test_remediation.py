import numpy as np
import pandas as pd
import pytest
from hotel_cancel.calibration_challenger import fit_mask,fit_calibrator,apply_calibration


def test_fit_mask_disjoint_and_mature():
 arrival=pd.Series(pd.to_datetime(['2016-06-30','2016-07-01','2016-09-30','2016-10-01','2017-01-01']))
 status=pd.Series(pd.to_datetime(['2016-06-30','2016-07-01','2016-10-01','2016-10-01','2017-01-01']))
 assert fit_mask(arrival,status).tolist()==[False,True,False,False,False]


def artifact():
 p=pd.Series([.1,.2,.7,.9]);y=pd.Series([0,0,1,1]);dates=pd.Series(pd.to_datetime(['2016-07-01']*4))
 model,_=fit_calibrator(p,y,dates,dates)
 return dict(calibrator=model,base_model_sha256='base',horizon='booking_to_arrival',hotel='Resort Hotel')


def test_city_untouched_resort_monotone():
 p=np.array([.2,.1,.5,.9]);h=['City Hotel','Resort Hotel','Resort Hotel','Resort Hotel']
 out=apply_calibration(p,h,artifact(),base_model_sha256='base')
 assert out[0]==p[0] and np.all(np.diff(out[1:])>0) and np.all((out>=0)&(out<=1))

@pytest.mark.parametrize('kwargs',[dict(base_model_sha256='wrong'),dict(base_model_sha256='base',horizon='seven_days')])
def test_model_horizon_binding(kwargs):
 with pytest.raises(ValueError):apply_calibration([.5],['Resort Hotel'],artifact(),**kwargs)

@pytest.mark.parametrize('probabilities,hotels',[([np.nan],['Resort Hotel']),([1.1],['Resort Hotel']),([.5],['Unknown']),([.5,.6],['City Hotel'])])
def test_invalid_probability_contract(probabilities,hotels):
 with pytest.raises(ValueError):apply_calibration(probabilities,hotels,artifact(),base_model_sha256='base')


def test_calibration_inputs_must_align():
 with pytest.raises(ValueError):fit_calibrator(pd.Series([.1,.9]),pd.Series([0,1],index=[2,3]),pd.Series(pd.to_datetime(['2016-07-01']*2)),pd.Series(pd.to_datetime(['2016-07-01']*2)))
