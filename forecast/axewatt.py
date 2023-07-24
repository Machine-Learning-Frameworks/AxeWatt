import numpy as np
import pandas as pd
from axewatt_tools import AxewattTools
from pycaret.time_series import load_model
from pycaret.time_series import TSForecastingExperiment

class Axewatt:
    def __init__(self):
        self.tools = AxewattTools()
        self.regions = ['N', 'NE', 'S', 'SE']
    
    def get_model(self, region: str):
        model = load_model(f"./forecast/models/ONSModel_{region}",
                           verbose=False)
        
        return model
    
    def save(self, model, experiment: TSForecastingExperiment, region: str):
        experiment.save_model(model, f"./forecast/models/ONSModel_{region}")
    
    def create_models(self):
        for region in self.regions:
            try:
                model = self.get_model(region)
            except:
                timeseries_experiment = TSForecastingExperiment()

                data = self.tools.get_data(region)

                timeseries_experiment.setup(data, target="mwh",
                                            fh=3, fold=4, n_jobs=1,
                                            session_id=991, verbose=False)

                model = timeseries_experiment.create_model("exp_smooth",
                                                            verbose=False)
                
                tuned_model = timeseries_experiment.tune_model(model, n_iter=10, optimize="R2",
                                                               search_algorithm="grid", verbose=False)

                finalized_model = timeseries_experiment.finalize_model(tuned_model)

                self.save(finalized_model, timeseries_experiment, region)

    def predict_data(self): 
        predictions = None

        for index, region in enumerate(self.regions):
            model = self.get_model(region)

            period = np.arange(1, 500 + 1)
            prediction = model.predict(fh=period)

            if index == 0:
                predictions = pd.DataFrame(prediction, index=prediction.index)
                predictions.rename(columns={"mwh": f"MWh_{region}"}, inplace=True)
                predictions = predictions.round(3)
                predictions.index.name = "Datetime"
            else:
                predictions[f"MWh_{region}"] = np.round(prediction.values, 3)

        data = self.tools.data
        data = data.to_period("A")
        data = pd.concat([data, predictions])
        data.to_csv("./data/CURVA_CARGA_FORECAST.csv")

if __name__ == "__main__":
    axewatt = Axewatt()
    axewatt.create_models()
    axewatt.predict_data()