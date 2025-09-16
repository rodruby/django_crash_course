# Market Analysis Tool - User Instructions

## Overview

The Market Analysis Tool is a professional Django web application designed for real estate appraisers and analysts to process MLS (Multiple Listing Service) data, analyze market trends, and calculate time adjustments for comparable sales. The application provides sophisticated analysis capabilities including multiple time adjustment methodologies and interactive data visualizations.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Data Upload and Processing](#data-upload-and-processing)
3. [Market Analysis Features](#market-analysis-features)
4. [Time Adjustment Calculations](#time-adjustment-calculations)
5. [Understanding the Calculations](#understanding-the-calculations)
6. [Charts and Visualizations](#charts-and-visualizations)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Getting Started

### System Requirements

- Python 3.8 or higher
- Django 5.2.5
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection for CDN resources (Bootstrap, Chart.js)

### Installation and Setup

1. **Install Dependencies**
   ```bash
   cd firstproject
   pip install -r requirements.txt
   ```

2. **Run Database Migrations**
   ```bash
   python manage.py migrate
   ```

3. **Start the Development Server**
   ```bash
   python manage.py runserver
   ```

4. **Access the Application**
   Open your web browser and navigate to `http://localhost:8000/market/`

### Optional: Create Admin User
```bash
python manage.py createsuperuser
```

## Data Upload and Processing

### Supported File Formats

- **CSV files** (.csv) - Most common MLS export format
- **Excel files** (.xls, .xlsx) - Alternative MLS export format
- **Maximum file size**: 10 MB

### Required Data Columns

The following columns are **required** for analysis:

- **ClosePrice**: The final sale price of the property
- **CloseDate**: The date the sale closed
- **SqFtTotal** or **SqFtLivArea**: Total or living area square footage

### Optional Data Columns

These columns enhance the analysis when available:

- **MLSNumber**: Unique MLS identifier
- **StreetNumberNumeric**: House number
- **StreetName**: Street name
- **City**: City name
- **CDOM**: Cumulative days on market
- **ListPrice**: Original listing price
- **CurrentPrice**: Current listing price
- **PendingDate**: Date the sale went pending
- **View**: View type (Mountain, City, Water, etc.)
- **WaterView**: Whether property has water view (Yes/No)

### Data Upload Process

1. **Navigate to Upload Page**
   - Click "Upload Data" in the main navigation
   - Or go directly to `/market/upload/`

2. **Fill Out Upload Form**
   - **Property Address**: Enter the subject property address (optional but recommended)
   - **File**: Select your CSV or Excel file
   - **Save to Database**: Check this to store individual sales records (recommended for datasets under 1000 records)

3. **Submit and Process**
   - Click "Upload & Analyze"
   - The system will process your file and redirect to the analysis results

### Data Validation and Cleaning

The system automatically:

- Removes dollar signs and commas from price fields
- Converts text to proper numeric formats
- Parses dates in various formats
- Excludes records with missing required data
- Calculates price per square foot using living area first, then total area
- Reports the number of records processed and excluded

## Market Analysis Features

### Dashboard Overview

The analysis dashboard provides:

- **Summary Cards**: Key metrics at a glance
- **Interactive Charts**: Price and price-per-square-foot trends over time
- **Data Tables**: Monthly and yearly aggregated statistics
- **Trend Analysis**: Linear and polynomial trendlines
- **Individual Sales**: Detailed view of processed records

### Monthly Analysis Table

Shows for each month:
- **Sales Count**: Number of closed sales
- **Median Price**: Middle value of all sale prices
- **Median $/SF**: Middle value of price per square foot
- **Price Change**: Month-over-month percentage change in median price
- **$/SF Change**: Month-over-month percentage change in median $/SF

### Yearly Summary Table

Provides annual aggregations:
- **Total Sales**: Number of sales in the year
- **Median Price**: Median sale price for the year
- **Price Trends**: Year-over-year changes

## Time Adjustment Calculations

### Overview

Time adjustments account for market appreciation or depreciation between a comparable sale date and the effective appraisal date. The system provides multiple calculation methodologies for robust analysis.

### Creating a Time Adjustment Analysis

1. **Access Time Adjustment Tool**
   - From any analysis page, click "Time Adjustment"
   - Or navigate to `/market/analysis/{id}/time-adjustment/`

2. **Set Effective Date**
   - Enter the appraisal effective date
   - This is typically the date for which you need the market value

3. **Add Comparable Sales**
   - Click "Add Comparable" to add sales data
   - Enter for each comparable:
     - **Sale Date**: When the comparable sold
     - **Sale Price**: The comparable's sale price
     - **Square Footage**: Living area (optional but recommended)
     - **Address**: Property address (optional, for record keeping)

4. **Calculate Adjustments**
   - Click "Calculate Time Adjustments"
   - The system processes all methodologies automatically

### Time Adjustment Methodologies

#### 1. Monthly Median Method

**How it works:**
- Finds the median price/PSF for the month containing the effective date
- Finds the median price/PSF for the month containing the comparable sale date
- Calculates percentage difference

**Formula:**
```
Adjustment % = ((Effective Month Median - Sale Month Median) / Sale Month Median) × 100
```

**Best for:**
- Markets with consistent monthly data
- When you have sufficient sales in each month
- Short time periods (under 1 year)

#### 2. Linear Trendline Method

**How it works:**
- Performs linear regression on historical monthly median data
- Extrapolates trendline values for both dates
- Calculates percentage difference based on trendline

**Formula:**
```
Trendline Value = (Slope × Date Ordinal) + Intercept
Adjustment % = ((Effective Trendline - Sale Trendline) / Sale Trendline) × 100
```

**Best for:**
- Markets with steady, consistent trends
- Longer time periods
- When monthly data has gaps

#### 3. Polynomial Trendline Method (4th Degree)

**How it works:**
- Fits a 4th-degree polynomial to historical data
- Captures complex market patterns and cycles
- Calculates adjustment based on polynomial curve

**Best for:**
- Markets with cyclical patterns
- Complex appreciation/depreciation trends
- Long-term analysis with sufficient data points

### Interpreting Results

- **Positive Adjustment**: Market appreciation from sale date to effective date
- **Negative Adjustment**: Market depreciation from sale date to effective date
- **Zero Adjustment**: No significant market change

**Example:**
If a comparable sold 6 months ago and shows a +3.5% adjustment, it means the market has appreciated 3.5% since that sale, so you might add 3.5% to the comparable's sale price for current market value.

## Understanding the Calculations

### Price Per Square Foot Logic

The system calculates price per square foot using this hierarchy:
1. **SqFtLivArea** if available and > 0
2. **SqFtTotal** if SqFtLivArea not available
3. Skip the record if neither is available

### Data Aggregation

**Monthly Aggregation:**
- Groups sales by year-month (YYYY-MM format)
- Calculates median, mean, and count for each metric
- Computes month-over-month percentage changes

**Yearly Aggregation:**
- Groups sales by calendar year
- Provides annual summary statistics

### Trendline Mathematics

**Linear Regression:**
Uses least squares method to fit: `y = mx + b`
- m = slope (rate of change)
- b = y-intercept
- x = time (as ordinal date number)
- y = price or price per square foot

**Polynomial Regression:**
Fits: `y = a₄x⁴ + a₃x³ + a₂x² + a₁x + a₀`
- Captures non-linear market patterns
- More flexible but requires more data points

## Charts and Visualizations

### Interactive Features

All charts include:
- **Hover tooltips** with detailed information
- **Zoom and pan** capabilities
- **Legend toggle** to show/hide data series
- **Responsive design** for different screen sizes

### Chart Types

#### 1. Median Sale Price Chart
- Shows price trends over time
- Includes linear and polynomial trendlines
- Y-axis formatted as currency

#### 2. Price Per Square Foot Chart
- Displays $/SF trends
- Includes trendlines for market direction
- Helpful for size-adjusted comparisons

#### 3. Mini Trend Charts (Dashboard)
- Small sparkline charts for quick overview
- Embedded in the analysis list
- Shows general market direction

### Chart Data Export

While not built-in, chart data can be:
- Printed using browser print function
- Screenshot for reports
- Data extracted from monthly/yearly tables

## Best Practices

### Data Quality

1. **Clean Your MLS Export**
   - Remove test listings
   - Verify sale dates are accurate
   - Ensure price data is complete

2. **Use Recent Data**
   - Include at least 12 months of sales
   - More data improves trendline accuracy
   - Consider market cycle timing

3. **Geographic Consistency**
   - Use sales from similar market areas
   - Consider micro-market variations
   - Document any market boundary decisions

### Time Adjustment Guidelines

1. **Choose Appropriate Method**
   - **Monthly Median**: For stable markets with good monthly data
   - **Linear Trendline**: For consistent appreciation/depreciation
   - **Polynomial**: For complex or cyclical markets

2. **Validate Results**
   - Compare all three methods
   - Look for reasonableness
   - Consider external market factors

3. **Document Your Analysis**
   - Note which method you used and why
   - Save screenshots of charts
   - Keep records of data sources

### Performance Optimization

1. **File Size Management**
   - Files under 1MB process fastest
   - Consider breaking large datasets into periods
   - Use "Save to Database" selectively

2. **Browser Performance**
   - Close other browser tabs during upload
   - Use modern browsers for best chart performance
   - Clear browser cache if experiencing issues

## Troubleshooting

### Common Upload Issues

**"Missing required column" Error:**
- Verify your CSV has ClosePrice, CloseDate, and square footage columns
- Check for exact spelling and capitalization
- Ensure headers are in the first row

**"File too large" Error:**
- Reduce file size to under 10MB
- Split large datasets into multiple uploads
- Remove unnecessary columns before upload

**"Error processing file" Message:**
- Check date formats (YYYY-MM-DD preferred)
- Verify price fields don't have special characters beyond $ and ,
- Ensure numeric fields contain only numbers

### Data Quality Issues

**No Monthly Data Appearing:**
- Verify dates are properly formatted
- Check that CloseDate column exists
- Ensure there are valid sales in the time period

**Strange Price Values:**
- Check for trailing spaces in price fields
- Verify price format (avoid currency symbols other than $)
- Look for decimal vs. comma confusion

**Missing Chart Data:**
- Refresh the page
- Check browser console for JavaScript errors
- Try a different browser

### Performance Issues

**Slow Upload Processing:**
- Large files may take 30+ seconds
- Don't refresh the page during processing
- Consider breaking up very large datasets

**Charts Not Loading:**
- Ensure internet connection for CDN resources
- Check browser JavaScript is enabled
- Try clearing browser cache

### Getting Help

If you encounter issues not covered here:

1. **Check the Browser Console**
   - Press F12 to open developer tools
   - Look for error messages in the Console tab

2. **Verify Data Format**
   - Compare your file to the provided sample_data.csv
   - Test with the sample file first

3. **System Requirements**
   - Ensure you're using a supported browser
   - Verify Python and Django versions match requirements

## Advanced Features

### Admin Interface

Access the Django admin at `/admin/` to:
- View detailed upload records
- Manage user accounts
- Export analysis results
- Clean up old data

### Database Integration

When "Save to Database" is enabled:
- Individual sale records are stored
- Enables complex queries and analysis
- Useful for large datasets and historical tracking
- Can be exported via admin interface

### API Considerations

The application is built with Django's class-based views and could be extended with:
- REST API endpoints
- Batch processing capabilities
- Automated report generation
- Integration with external MLS systems

## Conclusion

The Market Analysis Tool provides professional-grade real estate market analysis capabilities with multiple time adjustment methodologies, interactive visualizations, and robust data processing. By following these instructions and best practices, you can produce reliable market analysis for appraisal and real estate professional use.

For technical support or feature requests, refer to the application's documentation or contact your system administrator.