import pandas as pd

class AxewattTools:
    def __init__(self):
        self.data = pd.read_csv("./data/CURVA_CARGA.csv")
        self.data["Datetime"] = pd.to_datetime(self.data["Datetime"])
        self.data.set_index("Datetime", inplace=True)
        self.data = self.data.resample('a').sum()
        self.data = self.data[1:]

    
    def get_data(self, region: str) -> pd.DataFrame:
        df = self.data.rename(columns={f"MWh_{region}": "mwh"})

        return pd.DataFrame(df.mwh)