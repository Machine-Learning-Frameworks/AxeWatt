import numpy as np
import pandas as pd
from axewatt_tools import AxewattTools
from pycaret.time_series import load_model, save_model
from pycaret.time_series import TSForecastingExperiment

class Axewatt:
    def __init__(self):
        self.tools = AxewattTools()
        self.tools.update_csv()

        self.regions = ['N', 'NE', 'S', 'SE']
        self.models = []
        self.data = None
    
    def get_model(self, region: str):
        model = load_model(f"./models/ONSModel_{region}",
                           verbose=False)
        
        return model
    
    def save(model, region: str):
        save_model(model, f"./models/ONSModel_{region}")
    
    def create_models(self):
        for region in self.regions:
            try:
                model = self.get_model(region)
                
                new_data = self.tools.get_new_data(region)

                updated_model = model.update(y=new_data, update_params=True)
                self.models.append(updated_model)
            except:
                timeseries_experiment = TSForecastingExperiment()

                old_data = self.tools.get_data(region)
                new_data = self.tools.get_new_data(region)

                data = pd.concat([old_data, new_data])

                timeseries_experiment.setup(data, target="mwh",
                                            fh=24, max_sp_to_consider=24,
                                            session_id=991, verbose=False)

                model = timeseries_experiment.create_model("arima",
                                                            verbose=False)

                finalized_model = timeseries_experiment.finalize_model(model,
                                                                       verbose=False)

                self.models.append(finalized_model)
        
        if len(self.models) == 4:
            for index, region in enumerate(self.regions):
                self.save(self.models[index], region)
            
            self.models = []
        else:
            raise Exception("Error while creating models!")

    def update_data(self):
        old_data = pd.read_csv("../data/CURVA_CARGA.csv")
        new_data = pd.read_csv("../data/CURVA_CARGA_NOVO.csv")

        data = pd.concat([old_data, new_data])
        data["Datetime"] = pd.to_datetime(data["Datetime"])
        data.set_index("Datetime", inplace=True)
        data = data.asfreq('h')

        data.MWh_N = self.tools.fill_seasonal_hourly_missing_values(data.MWh_N.values)
        data.MWh_NE = self.tools.fill_seasonal_hourly_missing_values(data.MWh_NE.values)
        data.MWh_S = self.tools.fill_seasonal_hourly_missing_values(data.MWh_S.values)
        data.MWh_SE = self.tools.fill_seasonal_hourly_missing_values(data.MWh_SE.values)

        self.data = data
        self.data.to_csv("../data/CURVA_CARGA.csv")

    def predict_data(self): 
        predictions = None

        for index, model in enumerate(self.models):
            start_date = pd.date_range(start=self.data.index[-1], 
                                       periods=2, freq='h')

            data = pd.DataFrame(data={"mwh": np.zeros(24)},
                                index=pd.date_range(start=start_date[-1],
                                                    periods=24, freq='h'))
            
            data = self.tools.creature_features(data)
            data.drop(columns=["mwh"], inplace=True)

            prediction = model.predict(fh=np.arange(1, 25),
                                       X=data)

            if predictions == None:
                prediction = pd.DataFrame(prediction, index=np.arange(len(prediction)))
                prediction["Datetime"] = pd.date_range(start=start_date[-1],
                                                    periods=len(prediction), freq='h')

                prediction.set_index("Datetime", inplace=True)
                predictions = pd.DataFrame(data={f"MWh_{self.regions[index]}": prediction.mwh.values},
                                        index=prediction.index)
            else:
                prediction[f"MWh_{self.regions[index]}"] = prediction.values

        predictions.to_csv("../data/CURVA_CARGA_FORECAST.csv")

if __name__ == "__main__":
    axewatt = Axewatt()
    axewatt.create_models()
    axewatt.update_data()
    axewatt.predict_data()