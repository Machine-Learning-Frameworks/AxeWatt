import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_folium import folium_static
import datetime
import geopandas as gpd
import altair as alt

st.set_page_config(page_title='Forecasting',layout='wide')

pagina = st.empty()
@st.cache_data
def coleta_dados_csv():
  dados=pd.read_csv('data/CURVA_CARGA_FORECAST.csv')
  dados.rename(columns={'MWh_N':'Norte','MWh_NE':'Nordeste','MWh_S':'Sul','MWh_SE':'Centro-sul'})
  return dados


@st.cache_data
def coleta_localizacao():
  localizacao = gpd.read_file('WebPage/grandes_regioes_json.geojson')
  return localizacao
  
def filtra_dados(região,tempo_inicial,tempo_final):
  escala_do_dia = pd.date_range(start=tempo_inicial, end=tempo_final)
  tempo_inicial=datetime.datetime(tempo_inicial.year,tempo_inicial.month,tempo_inicial.day,0,0,0)
  tempo_final=datetime.datetime(tempo_final.year,tempo_final.month,tempo_final.day,23,0,0)
  data_frame=coleta_dados_csv()[[região,'Datetime']]
  data_frame['Datetime']=pd.to_datetime(data_frame['Datetime'])

  if tempo_inicial.year != tempo_final.year:
    filtrados=data_frame.loc[(data_frame['Datetime']>=tempo_inicial)&(data_frame['Datetime']<=tempo_final)]
    filtrados['Datetime'] = pd.DatetimeIndex(filtrados['Datetime'])
    filtrados.set_index('Datetime',inplace=True)
    filtrados = filtrados.resample('Y').sum()
    filtrados.reset_index(inplace=True)
    ano = filtrados['Datetime'].dt.strftime("%Y")
    filtrados['Datetime']= ano
    filtrados.rename(columns={região:'Mhw','Datetime':'Tempo'},inplace=True)
    return filtrados
    
  elif tempo_inicial.month != tempo_final.month and len(escala_do_dia) > 90 :
    filtrados=data_frame.loc[(data_frame['Datetime']>=tempo_inicial)&(data_frame['Datetime']<=tempo_final)]
    filtrados['Datetime'] = pd.DatetimeIndex(filtrados['Datetime'])
    filtrados.set_index('Datetime',inplace=True)
    filtrados = filtrados.resample('M').sum()
    filtrados.reset_index(inplace=True)
    mes = filtrados['Datetime'].dt.strftime("%m")
    filtrados['Datetime']=mes
    filtrados.rename(columns={região:'Mhw','Datetime':'Tempo'},inplace=True)
    return filtrados
    
  elif tempo_inicial.day != tempo_final.day : 
    filtrados=data_frame.loc[(data_frame['Datetime']>=tempo_inicial)&(data_frame['Datetime']<=tempo_final)]
    filtrados['Datetime'] = pd.DatetimeIndex(filtrados['Datetime'])
    filtrados.set_index('Datetime',inplace=True)
    filtrados= filtrados.resample('D').sum()
    filtrados.reset_index(inplace=True)
    filtrados['Datetime']=filtrados['Datetime'].dt.strftime("%m/%d")
    filtrados.rename(columns={região:'Mhw','Datetime':'Tempo'},inplace=True)
    return filtrados
  
  else:
    filtrados=data_frame.loc[(data_frame['Datetime']>=tempo_inicial)&(data_frame['Datetime']<=tempo_final)]
    filtrados['Datetime']= filtrados['Datetime'].copy().dt.strftime("%H:%M")
    filtrados.rename(columns={região:'Mhw','Datetime':'Tempo'},inplace=True)
    return filtrados
    
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
    
    
  
  st.subheader("Gráfico de Demanda")
  return grafico_real


def filtra_dados_comparação(região):
 dados = coleta_dados_csv()[[região,'Datetime']]
 tempo = pd.DatetimeIndex(dados['Datetime'].iloc[-24:]).strftime("%H:%M")
 dados_grafico = [dados[região].iloc[-24:].values,dados[região].iloc[-48:-24].values]
 dic = {'real':dados_grafico[0],'previsto':dados_grafico[1]}
 return pd.DataFrame(index=tempo, data=dic)

  
@st.cache_data(experimental_allow_widgets=True)
def cria_mapa(cores):

    dados=coleta_dados_csv()
    carga_estados={'Estados':[],
               'Mhw':[]}
    estados=['Nordeste','Norte','Sul','Centro-sul']
    for i in estados:
      carga_estados['Estados'].append(i)
      carga_estados['Mhw'].append(dados[i].iloc[-24::].sum().round())

    carga_estados=pd.DataFrame(carga_estados)
    mapa = folium.Map(location=[-14.235,-54.2],zoom_start=4,
                    max_zoom=4,min_zoom=4,tiles='CartoDB positron',dragging=False,prefer_canvas=True)
  
    carga_estados['cores']=cores
          
    cloropleth = folium.Choropleth(
        geo_data=coleta_localizacao(),
        data=carga_estados,
        columns=['Estados','cores'],
        key_on='feature.properties.NOME2',
        fill_color='Spectral'
        )
    carga_estados.set_index('Estados',inplace=True)
    cloropleth.geojson.add_to(mapa)
    for features in cloropleth.geojson.data['features']:
        features['properties']['MHW'] = "Consumo nas últimas 24 horas: "+ str(carga_estados.loc[features['properties']['NOME2']]['Mhw'])+' Mhw'
          
    cloropleth.geojson.add_child(
          folium.features.GeoJsonTooltip(['NOME2','MHW'],labels=False)
        )
    st.subheader("Região Selecionada")
    st_mapa=st_folium(mapa,width=1000, height=450) 
   
       
def home():
    
  
    st.sidebar.image('WebPage/LOGO.png')
    
    opção_regiao = st.sidebar.selectbox('Escolha uma região',('Norte','Nordeste','Centro-sul','Sul')) 
  
    col1, col2, col3 = st.columns(3)
    
    col1.metric(label = "Consumo na próxima hora: ", value = f"{coleta_dados_csv()[opção_regiao].iloc[-1]} MWh",
               delta = f"{(coleta_dados_csv()[opção_regiao].iloc[-1] - coleta_dados_csv()[opção_regiao].iloc[-2]).round()} MWh",
               help = f"Valor do consumo de energia previsto para ás {pd.to_datetime(coleta_dados_csv()['Datetime'].iloc[-1]).strftime('%H:%M na data %d/%m/%y')}" )
    col2.metric(label = "Consumo na última hora: ",value = f"{coleta_dados_csv()[opção_regiao].iloc[-2]} MWh" ,
               delta = f"{(coleta_dados_csv()[opção_regiao].iloc[-2] - coleta_dados_csv()[opção_regiao].iloc[-3]).round()} MWh",
               help = f"Valor do consumo de energia ás {pd.to_datetime(coleta_dados_csv()['Datetime'].iloc[-2]).strftime('%H:%M na data %d/%m/%y')}")
    col3.metric(label  ="Pico de consumo nas últimas 24 horas: ", value=f"{coleta_dados_csv()[opção_regiao].iloc[-24:-1].max()} MWh", 
               delta = f"{(coleta_dados_csv()[opção_regiao].iloc[-48:-24].max() - coleta_dados_csv()[opção_regiao].iloc[-24:-1].max()).round()} MWh",
               help = f"Valor do consumo de energia ás {pd.to_datetime(coleta_dados_csv()['Datetime'].iloc[coleta_dados_csv()[opção_regiao].iloc[-24:-1].idxmax()]).strftime('%H:%M na data %d/%m/%y')}")


    if opção_regiao == 'Centro-sul':
      cria_mapa([None,None,None,200])
    if opção_regiao == 'Nordeste':
      cria_mapa([200,None,None,None])
    if opção_regiao == 'Norte':
      cria_mapa([None,200,None,None])
    if opção_regiao == 'Sul':
      cria_mapa([None,None,200,None])
    dados_tempo=coleta_dados_csv()
  
    inicio=pd.to_datetime(dados_tempo['Datetime']).iloc[0]
    fim=pd.to_datetime(dados_tempo['Datetime']).iloc[-1]
    opção_tempo_inicial = st.sidebar.date_input('Escolha uma data inicial',fim,min_value=inicio,
                                              max_value=fim,
                                              )
    
    
  
    opção_tempo_final = st.sidebar.date_input('Escolha uma data final',opção_tempo_inicial,min_value=opção_tempo_inicial,
                                              max_value=fim,
                                              )

    
    
    st.altair_chart(cria_grafico_consumo(filtra_dados(opção_regiao,opção_tempo_inicial,opção_tempo_final)), theme="streamlit", use_container_width=True)
    





home()
