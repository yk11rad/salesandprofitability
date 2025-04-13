import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Set random seed to ensure consistent results across runs
np.random.seed(42)
random.seed(42)

# Define core parameters for synthetic data generation
num_records = 1000  # Total number of sales transactions
products = ['Laptop', 'Smartphone', 'Tablet', 'Headphones', 'Monitor']
regions = ['North', 'South', 'East', 'West']
start_date = datetime(2023, 1, 1)
end_date = datetime(2024, 12, 31)

# Establish product-specific price ranges for realistic data
product_prices = {
    'Laptop': (800, 1500),
    'Smartphone': (400, 900),
    'Tablet': (200, 600),
    'Headphones': (50, 300),
    'Monitor': (150, 800)
}

# Define a function to generate random dates within a specified range
def random_dates(start, end, n):
    """
    Generate random dates within a specified range
    
    Args:
        start: datetime - Start of date range
        end: datetime - End of date range
        n: int - Number of dates to generate
    
    Returns:
        List of datetime objects
    """
    date_range = (end - start).days
    return [start + timedelta(days=random.randint(0, date_range)) for _ in range(n)]

# Generate synthetic sales data with key attributes
data = {
    'Transaction_ID': [f'TX-{i:05d}' for i in range(1, num_records + 1)],
    'Date': random_dates(start_date, end_date, num_records),
    'Product': [random.choice(products) for _ in range(num_records)],
    'Region': [random.choice(regions) for _ in range(num_records)],
    'Units_Sold': np.random.randint(1, 50, size=num_records),
    'Customer_ID': np.random.randint(10000, 99999, size=num_records)  # Unique customer identifiers
}

# Create the initial DataFrame from the synthetic data
df = pd.DataFrame(data)

# Assign realistic pricing based on product type
df['Unit_Price'] = df['Product'].map(lambda x: np.random.uniform(*product_prices[x]))
df['Unit_Cost'] = np.minimum(df['Unit_Price'] * 0.9, df['Unit_Price'] * np.random.uniform(0.6, 0.9))

# Incorporate time-based patterns for enhanced realism
df['Day_of_Week'] = df['Date'].dt.dayofweek
df['Month'] = df['Date'].dt.month
df['Is_Holiday'] = df['Month'].isin([12, 1]).astype(int)  # Flag for holiday periods (Dec-Jan)
df['Units_Sold'] = df['Units_Sold'] * (1 + df['Is_Holiday'] * 0.3 + (df['Day_of_Week'] > 4) * 0.2)  # Increase sales during holidays and weekends

# Calculate essential financial metrics
df['Total_Sales'] = df['Units_Sold'] * df['Unit_Price']
df['Total_Cost'] = df['Units_Sold'] * df['Unit_Cost']
df['Profit'] = df['Total_Sales'] - df['Total_Cost']
df['Profit_Margin'] = (df['Profit'] / df['Total_Sales']) * 100

# Add time aggregations for trend analysis
df['Month_Year'] = df['Date'].dt.to_period('M').astype(str)  # Year-month format
df['Quarter'] = df['Date'].dt.to_period('Q').astype(str)
df['Cohort_Month'] = (df['Date'] + pd.offsets.MonthBegin(-1)).dt.to_period('M').astype(str)  # Customer cohort tracking

# Optimize DataFrame performance with categorical data types
df['Product'] = df['Product'].astype('category')
df['Region'] = df['Region'].astype('category')

# Validate data integrity with assertions
assert df['Unit_Cost'].le(df['Unit_Price']).all(), "Unit cost exceeds unit price in some records!"
assert df.duplicated(subset=['Transaction_ID']).sum() == 0, "Duplicate transaction IDs detected!"

# Implement a star schema with dimension tables
product_dim = df[['Product']].drop_duplicates().reset_index(drop=True)
product_dim['Product_ID'] = product_dim.index + 1000

region_dim = df[['Region']].drop_duplicates().reset_index(drop=True)
region_dim['Region_ID'] = region_dim.index + 2000

# Construct the fact table by merging with dimension tables
fact_table = df.merge(product_dim, on='Product').merge(region_dim, on='Region')
fact_table = fact_table.drop(columns=['Product', 'Region']).rename(columns={
    'Product_ID': 'Product_ID', 'Region_ID': 'Region_ID'
})

# Perform aggregations for dashboard visualizations
sales_by_product = fact_table.groupby('Product_ID').agg({
    'Total_Sales': 'sum',
    'Profit': 'sum',
    'Units_Sold': 'sum',
    'Profit_Margin': 'mean'
}).reset_index().merge(product_dim, on='Product_ID')
sales_by_product.columns = ['Product_ID', 'Total_Sales', 'Total_Profit', 'Units_Sold', 'Avg_Profit_Margin', 'Product']

sales_trends = fact_table.groupby('Month_Year').agg({
    'Total_Sales': 'sum',
    'Profit': 'sum'
}).reset_index()

sales_by_region = fact_table.groupby('Region_ID').agg({
    'Total_Sales': 'sum',
    'Profit': 'sum',
    'Units_Sold': 'sum'
}).reset_index().merge(region_dim, on='Region_ID')
sales_by_region.columns = ['Region_ID', 'Total_Sales', 'Total_Profit', 'Units_Sold', 'Region']

# Calculate RFM segmentation for customer analysis
snapshot_date = fact_table['Date'].max() + timedelta(days=1)
rfm = fact_table.groupby('Customer_ID').agg({
    'Date': lambda x: (snapshot_date - x.max()).days,  # Recency
    'Transaction_ID': 'count',  # Frequency
    'Total_Sales': 'sum'  # Monetary
}).rename(columns={'Date': 'Recency', 'Transaction_ID': 'Frequency', 'Total_Sales': 'Monetary'})

# Export datasets in efficient Parquet format and Excel for BI tools
fact_table.to_parquet('sales_fact_table.parquet', index=False)
product_dim.to_parquet('product_dimension.parquet', index=False)
region_dim.to_parquet('region_dimension.parquet', index=False)

with pd.ExcelWriter('sales_profitability_dashboard.xlsx') as writer:
    fact_table.to_excel(writer, sheet_name='Transactions', index=False)
    sales_by_product.to_excel(writer, sheet_name='Product_Performance', index=False)
    sales_trends.to_excel(writer, sheet_name='Sales_Trends', index=False)
    sales_by_region.to_excel(writer, sheet_name='Region_Performance', index=False)
    rfm.to_excel(writer, sheet_name='RFM_Segmentation', index=False)

# Display sample data for verification purposes
print("Sample Fact Table:")
print(fact_table.head())
print("\nSales by Product:")
print(sales_by_product.head())
print("\nSales Trends by Month:")
print(sales_trends.head())
print("\nSales by Region:")
print(sales_by_region.head())
print("\nRFM Segmentation:")
print(rfm.head())

# Provide visualization suggestions for Power BI/Tableau integration
# 1. Bar Chart: Total Sales and Profit by Product (Product_Performance)
# 2. Line Chart with Moving Average: Sales and Profit Trends (Sales_Trends)
# 3. Regional Map: Sales and Profit by Region (Region_Performance)
# 4. Waterfall Chart: Profit Drivers by Product (Product_Performance)
# 5. Heatmap: Sales by Day of Week vs. Holiday (Transactions)
# 6. RFM Scatter Plot: Customer Segmentation (RFM_Segmentation)

# README Section
# Welcome to the Sales & Profitability Dashboard script! This tool generates synthetic sales data and prepares it for visualization in Power BI or Tableau, offering insights into sales trends, profitability, and customer behavior.
# 
# Key Features:
# - Generates realistic sales data for 1,000 transactions across five products and four regions, with product-specific pricing and seasonal adjustments (e.g., holiday and weekend sales boosts).
# - Utilizes pandas and numpy for efficient data manipulation, implementing a star schema with dimension and fact tables for scalability.
# - Calculates financial metrics (sales, profit, margins) and customer RFM segmentation (Recency, Frequency, Monetary) for advanced analysis.
# - Exports data in Parquet and Excel formats, optimized for BI tool integration.
# 
# How to Use:
# 1. Run the script to generate and process the data.
# 2. Import the output files (e.g., 'sales_fact_table.parquet' or 'sales_profitability_dashboard.xlsx') into Power BI or Tableau.
# 3. Create visualizations based on the suggested charts (e.g., bar charts for product performance, line charts for trends).
# 
# Requirements:
# - Python 3.8+ with pandas, numpy, and openpyxl libraries installed.
# 
# Output Files:
# - 'sales_fact_table.parquet': Detailed transaction data.
# - 'product_dimension.parquet': Product lookup table.
# - 'region_dimension.parquet': Region lookup table.
# - 'sales_profitability_dashboard.xlsx': Aggregated data across multiple sheets (Transactions, Product_Performance, etc.).
# 
# This script is designed to demonstrate data processing and analytical skills for financial dashboard development. Feel free to explore the code and adapt it for your needs!