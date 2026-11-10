"""Optional MLflow research wrapper; unchanged base learner plus bound calibrator."""
import hashlib
import joblib
from hotel_cancel.registry_model import HotelBookingModel
from hotel_cancel.calibration_challenger import apply_calibration

class CalibratedHotelBookingModel(HotelBookingModel):
 def load_context(self,context):
  super().load_context(context)
  self.calibration=joblib.load(context.artifacts['booking_calibrator'])
  self.base_sha=hashlib.sha256(open(context.artifacts['booking_bundle'],'rb').read()).hexdigest()
  if self.calibration['base_model_sha256']!=self.base_sha:raise ValueError('Calibrator/base mismatch')
 def predict(self,context,model_input,params=None):
  result=super().predict(context,model_input,params)
  result['cancellation_probability']=apply_calibration(result['cancellation_probability'].to_numpy(),
    model_input['hotel'].to_numpy(),self.calibration,base_model_sha256=self.base_sha)
  return result
