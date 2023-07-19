import numpy as np
import pandas as pd
import requests

class AxewattTools:
    def __init__(self):
        self.url = 'https://ons-dl-prod-opendata.s3.amazonaws.com/dataset/curva-carga-ho/CURVA_CARGA_2023.csv'
        self.response = requests.get(self.url)

    def fill_seasonal_hourly_missing_values(self, values: np.ndarray):
        for index, value in enumerate(values):
            if np.isnan(value):
                values[index] = values[index - 24*7]

        return values

    def update_csv(self):
        def string_to_dataframe(string_data):
            lines = string_data.split('\n')
            rows = [line.split(';') for line in lines]
            df = pd.DataFrame(rows[1:], columns=rows[0])
    
            return df
        
        def get_all_data(df: pd.DataFrame):
            all_data = None

            for index, region in enumerate(['N', 'NE', 'S', 'SE']):
                dfR = df[df["ID_Subsys"] == f'{region}']
                dfR.drop(columns=["ID_Subsys"], inplace=True)
                dfR["MWh"] = dfR['MWh'].astype(float)
                dfR = dfR.round(decimals=3)
                dfR = dfR.rename(columns={"MWh": f"MWh_{region}"})
                dfR = dfR.asfreq('h')
                dfR[f"MWh_{region}"] = self.fill_seasonal_hourly_missing_values(dfR[f"MWh_{region}"].values)

                if index == 0:
                    all_data = dfR
                else:
                    all_data[f"MWh_{region}"] = dfR[f"MWh_{region}"]

            return all_data
        
        if self.response.status_code == 200:
            content = self.response.content.decode('utf-8')
        
        df = string_to_dataframe(content)
        df = df.drop(columns=["nom_subsistema"])
        df = df.rename(columns={"id_subsistema": "ID_Subsys", 
                                "din_instante": "Datetime", 
                                "val_cargaenergiahomwmed": "MWh"})
        
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        df.set_index(["Datetime"], inplace=True)

        data = get_all_data(df)
        old_data = pd.read_csv("./data/CURVA_CARGA.csv")
        old_data["Datetime"] = pd.to_datetime(old_data["Datetime"])

        new_data = data.drop(data.loc[data.index <= old_data.iloc[-1]["Datetime"]].index)
        new_data.to_csv("./data/CURVA_CARGA_NOVO.csv")

    def create_features(self, df) -> pd.DataFrame:
        df["date"] = df.index
        df["dayofweek"] = df["date"].dt.dayofweek
        df["quarter"] = df["date"].dt.quarter
        df["month"] = df["date"].dt.month
        df["year"] = df["date"].dt.year
        df["dayofyear"] = df["date"].dt.dayofyear
        df["dayofmonth"] = df["date"].dt.day
        df["weekofyear"] = df["date"].dt.weekofyear

        covid_start = np.datetime64("2020-03-03 00:00:00")
        covid_end = np.datetime64("2023-05-05 00:00:00")
        bool_df = df["date"] >= covid_start
        bool_df = bool_df.where(bool_df.index <= covid_end)
        bool_df.fillna(False, inplace=True)

        df["flag"] = pd.Series(np.where(bool_df, 1, 0),
                                index=df.index)

        X = df[["dayofweek", "quarter", "month", "year",
                "dayofyear", "dayofmonth", "weekofyear", "flag", "mwh"]]
        X.index = df.index

        return X
    
    def get_data(self, region: str) -> pd.DataFrame:
        df = pd.read_csv("../data/CURVA_CARGA.csv")
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        df.set_index("Datetime", inplace=True)
        df = df.asfreq('h')

        df[f"MWh_{region}"] = self.fill_seasonal_hourly_missing_values(df[f"MWh_{region}"].values)

        df.rename(columns={f"MWh_{region}": "mwh"}, inplace=True)
        df = self.create_features(df)
        return pd.DataFrame(df.mwh)

    def get_new_data(self, region: str) -> pd.DataFrame:
        df = pd.read_csv("../data/CURVA_CARGA_NOVO.csv")
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        df.drop_duplicates(subset=["Datetime"], inplace=True)
        df.set_index("Datetime", inplace=True)
        df = df.asfreq('h')

        df[f"MWh_{region}"] = self.fill_seasonal_hourly_missing_values(df[f"MWh_{region}"].values)

        df.rename(columns={f"MWh_{region}": "mwh"}, inplace=True)
        df = self.create_features(df)
        return pd.DataFrame(df.mwh)