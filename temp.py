# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
#import libraries
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

#define functions
def style_negative(v,props=''):
    """Style negative values in dataframe """
    try:
        return props if v <0 else None
    except:
        pass
    
def style_positive(v,props=''):
    """ style positive values in dataframe """
    try:
        return props if v>0 else None
    except:
        pass
    
def audience_simple(country):
    """ Show top countries"""
    if country == 'US':
        return 'USA'
    elif country == 'IN':
        return 'India'
    else: return 'Other'
    
    


#load data
@st.cache_data  # Updated decorator
def load_data():
    """ Loads in 4 dataframes and does light feature engineering"""
    df_agg = pd.read_csv('Aggregated_Metrics_By_Video.csv').iloc[1:, :]
    df_agg.columns = ['Video', 'Video title', 'Video publish time', 'Comments added', 'Shares', 'Dislikes', 'Likes',
                      'Subscribers lost', 'Subscribers gained', 'RPM(USD)', 'CPM(USD)', 'Average % viewed',
                      'Average view duration', 'Views', 'Watch time (hours)', 'Subscribers',
                      'Your estimated revenue (USD)', 'Impressions', 'Impressions ctr(%)']
    
    # Fix datetime parsing issues
    df_agg['Video publish time'] = pd.to_datetime(df_agg['Video publish time'], errors='coerce')
    df_agg['Average view duration'] = pd.to_timedelta(df_agg['Average view duration'], errors='coerce')
    
    # Create Avg_duration_sec feature
    df_agg['Avg_duration_sec'] = df_agg['Average view duration'].dt.total_seconds()
    
    # Additional features
    df_agg['Engagement_ratio'] = (df_agg['Comments added'] + df_agg['Shares'] + df_agg['Dislikes'] + df_agg['Likes']) / df_agg['Views']
    df_agg['Views / sub gained'] = df_agg['Views'] / df_agg['Subscribers gained']
    df_agg.sort_values('Video publish time', ascending=False, inplace=True)
    
    # Load additional CSV files
    df_agg_sub = pd.read_csv('Aggregated_Metrics_By_Country_And_Subscriber_Status.csv')
    df_comments = pd.read_csv('Aggregated_Metrics_By_Video.csv')
    df_time = pd.read_csv('Video_Performance_Over_Time.csv')
    df_time['Date'] = pd.to_datetime(df_time['Date'], errors='coerce')
    
    return df_agg, df_agg_sub, df_comments, df_time

# Create dataframes from the function
df_agg, df_agg_sub, df_comments, df_time = load_data()

# engineer data

# Copy the DataFrame
df_agg_diff = df_agg.copy()

# Calculate the date 12 months before the max date
metric_date_12mo = df_agg_diff['Video publish time'].max() - pd.DateOffset(months=12)

# Select numeric columns only
numeric_cols = df_agg_diff.select_dtypes(include=['float64', 'int64']).columns

# Compute the median for numeric columns within the 12-month window
median_agg = df_agg_diff.loc[
    df_agg_diff['Video publish time'] >= metric_date_12mo, numeric_cols
].median()

# Apply the transformation to numeric columns
df_agg_diff[numeric_cols] = (df_agg_diff[numeric_cols] - median_agg).div(median_agg)



#merge daily data with publish data to get delta 
df_time_diff = pd.merge(df_time, df_agg.loc[:,['Video','Video publish time']], left_on ='External Video ID', right_on = 'Video')
df_time_diff['days_published'] = (df_time_diff['Date'] - df_time_diff['Video publish time']).dt.days

# get last 12 months of data rather than all data 
date_12mo = df_agg['Video publish time'].max() - pd.DateOffset(months =12)
df_time_diff_yr = df_time_diff[df_time_diff['Video publish time'] >= date_12mo]

# get daily view data (first 30), median & percentiles 
views_days = pd.pivot_table(df_time_diff_yr,index= 'days_published',values ='Views', aggfunc = [np.mean,np.median,lambda x: np.percentile(x, 80),lambda x: np.percentile(x, 20)]).reset_index()
views_days.columns = ['days_published','mean_views','median_views','80pct_views','20pct_views']
views_days = views_days[views_days['days_published'].between(0,30)]
views_cumulative = views_days.loc[:,['days_published','median_views','80pct_views','20pct_views']] 
views_cumulative.loc[:,['median_views','80pct_views','20pct_views']] = views_cumulative.loc[:,['median_views','80pct_views','20pct_views']].cumsum()



# what metrics will be relevant
# Difference from baseline
# Percent change by video

#building the dashboard
add_sidebar = st.sidebar.selectbox('Aggregate or Individual Video', ('Aggregate Metrics','Individual Video Analysis'))

#total picture# Total picture
if add_sidebar == 'Aggregate Metrics':
    df_agg_metrics = df_agg[['Video publish time', 'Views', 'Likes', 'Subscribers', 'Shares', 'Comments added', 
                             'RPM(USD)', 'Average % viewed', 'Avg_duration_sec', 'Engagement_ratio', 'Views / sub gained']]
    
    # Define the 6-month and 12-month cutoff dates
    metric_date_6mo = df_agg_metrics['Video publish time'].max() - pd.DateOffset(months=6)
    metric_date_12mo = df_agg_metrics['Video publish time'].max() - pd.DateOffset(months=12)
    
    # Exclude 'Video publish time' from median calculations
    numeric_cols = ['Views', 'Likes', 'Subscribers', 'Shares', 'Comments added', 
                    'RPM(USD)', 'Average % viewed', 'Avg_duration_sec', 'Engagement_ratio', 'Views / sub gained']
    
    # Compute medians
    metric_medians6mo = df_agg_metrics[df_agg_metrics['Video publish time'] >= metric_date_6mo][numeric_cols].median()
    metric_medians12mo = df_agg_metrics[df_agg_metrics['Video publish time'] >= metric_date_12mo][numeric_cols].median()
    
    # Display metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    columns = [col1, col2, col3, col4, col5]
    
    count = 0
    for i in metric_medians6mo.index:
        with columns[count]:
            delta = (metric_medians6mo[i] - metric_medians12mo[i]) / metric_medians12mo[i]
            st.metric(label=i, value=round(metric_medians6mo[i], 1), delta="{:.2%}".format(delta))
            count += 1
            if count >= 5:
                count = 0
      #get date information / trim to relevant data 
    df_agg_diff['Publish_date'] = df_agg_diff['Video publish time'].apply(lambda x: x.date())
    df_agg_diff_final = df_agg_diff.loc[:,['Video title','Publish_date','Views','Likes','Subscribers','Shares','Comments added','RPM(USD)','Average % viewed',
                             'Avg_duration_sec', 'Engagement_ratio','Views / sub gained']]
    
    # Create a formatting dictionary for numeric columns
    df_to_pct = {col: '{:.1%}'.format for col in numeric_cols}

    # Apply styling only to numeric columns
    st.dataframe(
        df_agg_diff_final.style
        .applymap(style_negative, subset=numeric_cols, props='color:red;')
        .applymap(style_positive, subset=numeric_cols, props='color:green;')
        .format(df_to_pct, subset=numeric_cols)
        )
    
    
#individual video
if add_sidebar == 'Individual Video Analysis':
    videos = tuple(df_agg['Video title'])
    video_select = st.selectbox('Pick a Video:',videos)
    
    agg_filtered = df_agg[df_agg['Video title'] == video_select]
    agg_sub_filtered = df_agg_sub[df_agg_sub['Video Title'] == video_select]
    agg_sub_filtered['Country'] = agg_sub_filtered['Country Code'].apply(audience_simple)
    agg_sub_filtered.sort_values('Is Subscribed', inplace= True)   
    
    fig = px.bar(agg_sub_filtered, x ='Views', y='Is Subscribed', color ='Country', orientation ='h')
    #order axis 
    st.plotly_chart(fig)
    
    
    agg_time_filtered = df_time_diff[df_time_diff['Video Title'] == video_select]
    first_30 = agg_time_filtered[agg_time_filtered['days_published'].between(0,30)]
    first_30 = first_30.sort_values('days_published')
    
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['20pct_views'],
                    mode='lines',
                    name='20th percentile', line=dict(color='purple', dash ='dash')))
    fig2.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['median_views'],
                        mode='lines',
                        name='50th percentile', line=dict(color='black', dash ='dash')))
    fig2.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['80pct_views'],
                        mode='lines', 
                        name='80th percentile', line=dict(color='royalblue', dash ='dash')))
    fig2.add_trace(go.Scatter(x=first_30['days_published'], y=first_30['Views'].cumsum(),
                        mode='lines', 
                        name='Current Video' ,line=dict(color='firebrick',width=8)))
        
    fig2.update_layout(title='View comparison first 30 days',
                   xaxis_title='Days Since Published',
                   yaxis_title='Cumulative views')
    
    st.plotly_chart(fig2)

    