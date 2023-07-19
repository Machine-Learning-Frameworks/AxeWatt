import numpy as np
import pandas as pd
from axewatt_tools import AxewattTools
from pycaret.time_series import load_model
from pycaret.time_series import TSForecastingExperiment

class Axewatt:
    def __init__(self):
        self.tools = AxewattTools()
        self.tools.update_csv()

        self.data = pd.read_csv("./data/CURVA_CARGA.csv")
        self.data["Datetime"] = pd.to_datetime(self.data["Datetime"])
        self.data.set_index("Datetime", inplace=True)
        self.data = self.data.asfreq('h')

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
                
                new_data = self.tools.get_new_data(region)

                updated_model = model.update(y=new_data, update_params=True)
                self.save(model, region)
            except:
                timeseries_experiment = TSForecastingExperiment()

                old_data = self.tools.get_data(region)
                new_data = self.tools.get_new_data(region)

                data = pd.concat([old_data, new_data])

                timeseries_experiment.setup(data, target="mwh",
                                            fh=24, max_sp_to_consider=24,
                                            session_id=991, verbose=False,
                                            n_jobs=1)

                model = timeseries_experiment.create_model("arima",
                                                            verbose=False)

                finalized_model = timeseries_experiment.finalize_model(model)

                self.save(finalized_model, timeseries_experiment, region)
        
        if len(self.models) != 4:
            raise Exception("Error while creating models!")

    def update_data(self):
        old_data = pd.read_csv("./data/CURVA_CARGA.csv")
        new_data = pd.read_csv("./data/CURVA_CARGA_NOVO.csv")

        data = pd.concat([old_data, new_data])
        data["Datetime"] = pd.to_datetime(data["Datetime"])
        data.drop_duplicates(subset=["Datetime"], inplace=True)
        data.set_index("Datetime", inplace=True)
        data = data.asfreq('h')

        data.MWh_N = self.tools.fill_seasonal_hourly_missing_values(data.MWh_N.values)
        data.MWh_NE = self.tools.fill_seasonal_hourly_missing_values(data.MWh_NE.values)
        data.MWh_S = self.tools.fill_seasonal_hourly_missing_values(data.MWh_S.values)
        data.MWh_SE = self.tools.fill_seasonal_hourly_missing_values(data.MWh_SE.values)

        self.data = data
        self.data.to_csv("./data/CURVA_CARGA.csv")

    def predict_data(self): 
        predictions = None

        for index, region in enumerate(self.regions):
            model = self.get_model(region)

            start_date = pd.date_range(start=self.data.index[-1], 
                                       periods=25, freq='h')
            
            dates = start_date[1:]

            data = pd.DataFrame(data={"mwh": np.zeros(24)},
                                index=dates)
            
            exogenous_data = self.tools.create_features(data)
            exogenous_data.drop(columns=["mwh"], inplace=True)
            exogenous_data.index = exogenous_data.index.to_period('h')
            
            period = np.arange(1, 25)

            prediction = model.predict(fh=period,
                                       X=exogenous_data)

            if index == 0:
                predictions = pd.DataFrame(prediction, index=prediction.index)
                predictions.rename(columns={"mwh": f"MWh_{region}"}, inplace=True)
                predictions = predictions.round(3)
                predictions.index.name = "Datetime"
            else:
                predictions[f"MWh_{region}"] = np.round(prediction.values, 3)

        data = pd.concat([self.data, predictions])
        data.to_csv("./data/CURVA_CARGA_FORECAST.csv")

if __name__ == "__main__":
    axewatt = Axewatt()
    # axewatt.create_models()
    # axewatt.update_data()
    axewatt.predict_data()