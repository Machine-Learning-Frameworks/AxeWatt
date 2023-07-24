import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_folium import folium_static
import datetime
import geopandas as gpd
import altair as alt




st.set_page_config(page_title='Forecasting',layout='wide')

if 'estado_escolhido' not in st.session_state:
  st.session_state['estado_escolhido'] = 'Centro-sul'

pagina = st.empty()

@st.cache_data
def coleta_dados_csv():
  dados=pd.read_csv('data/CURVA_CARGA_FORECAST.csv')
  dados.rename(columns={'MWh_N':'Norte','MWh_NE':'Nordeste','MWh_S':'Sul','MWh_SE':'Centro-sul'},inplace=True)
  return dados


@st.cache_data
def coleta_localizacao():
  localizacao = gpd.read_file('WebPage/grandes_regioes_json.geojson')
  return localizacao
  
def filtra_dados(região,ano_inicial,ano_final):

  
    dados=coleta_dados_csv()
    inicio = dados['Datetime'][dados['Datetime']==ano_inicial].index[0]
    fim = dados['Datetime'][dados['Datetime']==ano_final].index[0]
    ano = pd.date_range(start=datetime.datetime(dados['Datetime'].iloc[inicio],1,1), end=datetime.datetime(dados['Datetime'].iloc[fim],12,31),inclusive="both",freq='Y').strftime("%Y")
    dados = dados.iloc[inicio:fim+1]
    dados = dados[['Datetime',região]]
    dados['Datetime'] = ano
    dados.rename(columns={região:'Mhw','Datetime':'Tempo'},inplace=True)
    return dados

    
def cria_grafico_consumo(dados):
  grafico=alt.Chart(dados).mark_area(color = 'orange',
                           opacity = 0.5, line = {'color':'orange'}).encode(
    alt.X('Tempo',axis=alt.Axis(labelAngle=0)),
    alt.Y('Mhw',scale=alt.Scale(domain=[0, (dados['Mhw'].max()*1.3).round()])))
  
  pontos_proximos = alt.selection_point(nearest=True, on='mouseover',
                        fields=['Tempo','Mhw'], empty=False)
  seletores = alt.Chart(dados).mark_point().encode(
    x='Tempo',
    opacity=alt.value(0),
  ).add_params(
    pontos_proximos
  )
  pontos = grafico.mark_point().encode(
    opacity=alt.condition(pontos_proximos, alt.value(1), alt.value(0))
      )
  texto = grafico.mark_text(align='center', dx=0, dy=-30,color='orange',size=20).encode(
    text=alt.condition(pontos_proximos, 'label:N', alt.value(' '))
    
      ).transform_calculate(label='datum.Mhw + " MWh"')
  regua = alt.Chart(dados).mark_rule(color='gray').encode(
    x='Tempo',y='Mhw',
  ).transform_filter(
  pontos_proximos
  )
  
  grafico_real = alt.layer(
      seletores, pontos, texto, regua, grafico
      ).properties(
      width=1000, height=450
      ).configure_axis(labelLimit=250,labelFontSize=20,grid=True,title=None)
    
    
  

  return grafico_real


def ordena_regiões(ano_inicial,ano_final):
  dados = coleta_dados_csv()
  inicio = dados['Datetime'][dados['Datetime']==ano_inicial].index[0]
  fim = dados['Datetime'][dados['Datetime']==ano_final].index[0]
  percentuais_aumento = [(((dados['Norte'].iloc[fim]-dados['Norte'].iloc[inicio])/dados['Norte'].iloc[inicio])*100).round(),
                         (((dados['Sul'].iloc[fim]-dados['Sul'].iloc[inicio])/dados['Sul'].iloc[inicio])*100).round(),
                         (((dados['Nordeste'].iloc[fim]-dados['Nordeste'].iloc[inicio])/dados['Nordeste'].iloc[inicio])*100).round(),
                         (((dados['Centro-sul'].iloc[fim]-dados['Centro-sul'].iloc[inicio])/dados['Centro-sul'].iloc[inicio])*100).round()
                        ]
  return pd.Series(data = percentuais_aumento, index =['Norte','Sul','Nordeste','Centro-sul']).sort_values(ascending=False)



def home():
    
  
    st.sidebar.image('WebPage/LOGO.png')
    
    ano_inicial = st.sidebar.selectbox('Escolha o ano inicial',(coleta_dados_csv()['Datetime']))

    
    ano_final = st.sidebar.selectbox('Escolha o ano final',(coleta_dados_csv()['Datetime'].iloc[coleta_dados_csv()['Datetime'][coleta_dados_csv()['Datetime']==ano_inicial].index[0]+1:]))


    regiões = ordena_regiões(ano_inicial,ano_final)

    col1, col2, col3, col4 = st.columns(4)
   
    col1.metric(label = "", value = regiões.index[0] ,
               delta = f"{(regiões.iloc[0])}%",
               help = f"" )
    col2.metric(label = "" ,value = regiões.index[1],
               delta = f"{(regiões.iloc[1])}%",
               help = f"")
    col3.metric(label  ="",value = regiões.index[2],
               delta = f"{(regiões.iloc[2])}%",
               help = f"")
    col4.metric(label  ="",value = regiões.index[3],
               delta = f"{(regiões.iloc[3])}%",
               help = f"")
  
    dados = ordena_regiões(ano_inicial,ano_final).to_frame()
    dados['Estados'] = dados.index
    dados['index'] = [0,1,2,3]
    dados.set_index('index',inplace=True)
    dados.rename(columns={0:'Carga'},inplace = True)
    mapa = folium.Map(location=[-14.235,-54.2],zoom_start=4,
                    max_zoom=4,min_zoom=4,tiles='CartoDB positron',dragging=False,prefer_canvas=True)
  
          
    cloropleth = folium.Choropleth(
        geo_data=coleta_localizacao(),
        data=dados,
        columns=['Estados','Carga'],
        key_on='feature.properties.NOME2',
        fill_color='Spectral'
        )
    dados.set_index('Estados',inplace=True)
    cloropleth.geojson.add_to(mapa)
    for features in cloropleth.geojson.data['features']:
        features['properties']['MHW'] = "Variação percentual: "+ str(dados.loc[features['properties']['NOME2']]['Carga'])+'%'
          
    cloropleth.geojson.add_child(
          folium.features.GeoJsonTooltip(['NOME2','MHW'],labels=False)
        )
    st.subheader("Variação percentual por região:")
    st_mapa=st_folium(mapa,width=1000,height=450) 
    
    if st_mapa['last_active_drawing']:
     st.session_state['estado_escolhido'] = st_mapa['last_active_drawing']['properties']['NOME2']

    st.subheader("Demanda " + st.session_state['estado_escolhido'])
    st.altair_chart(cria_grafico_consumo(filtra_dados(st.session_state['estado_escolhido'],ano_inicial,ano_final)), theme="streamlit", use_container_width=True)
home()
