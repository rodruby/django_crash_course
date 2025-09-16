"""
time_adjustments.py

Advanced time adjustment calculations for real estate market analysis.
Provides multiple methodologies for calculating time adjustments between
comparable sales and effective appraisal dates.

Functions:
- calculate_monthly_adjustment: Uses monthly median data
- calculate_linear_trendline_adjustment: Linear regression-based adjustment
- calculate_polynomial_trendline_adjustment: 4th degree polynomial adjustment
- process_time_adjustments: Main function to calculate all adjustments
"""

import numpy as np
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
from decimal import Decimal, ROUND_HALF_UP
import logging

logger = logging.getLogger(__name__)


def find_closest_month_data(monthly_data: List[Dict], target_date: date) -> Optional[Dict]:
    """
    Find the monthly data entry closest to the target date.
    Returns the month ending prior to or on the target date.

    Args:
        monthly_data: List of monthly aggregation dictionaries
        target_date: The date to find closest month for

    Returns:
        Dictionary with monthly data or None if no suitable month found
    """
    if not monthly_data:
        return None

    # Convert target date to year-month string
    target_ym = target_date.strftime('%Y-%m')

    # Filter to months ending on or before target date
    valid_months = []
    for month in monthly_data:
        if month.get('year_month', '') <= target_ym:
            valid_months.append(month)

    if not valid_months:
        return None

    # Return the most recent valid month
    return max(valid_months, key=lambda x: x.get('year_month', ''))


def calculate_monthly_adjustment(
    monthly_data: List[Dict],
    effective_date: date,
    sale_date: date,
    metric: str = 'median_close'
) -> Optional[float]:
    """
    Calculate time adjustment using monthly median data.

    Finds the monthly median for the month ending prior to the effective date
    and the month of the sale date, then calculates percentage difference.

    Args:
        monthly_data: List of monthly aggregation dictionaries
        effective_date: The appraisal effective date
        sale_date: The comparable sale date
        metric: Either 'median_close' or 'median_pps'

    Returns:
        Percentage adjustment (positive means increase from sale to effective date)
    """
    try:
        effective_month_data = find_closest_month_data(monthly_data, effective_date)
        sale_month_data = find_closest_month_data(monthly_data, sale_date)

        if not effective_month_data or not sale_month_data:
            logger.warning(f"Missing month data for {metric} adjustment calculation")
            return None

        effective_value = effective_month_data.get(metric)
        sale_value = sale_month_data.get(metric)

        if not effective_value or not sale_value or sale_value == 0:
            logger.warning(f"Invalid values for {metric}: effective={effective_value}, sale={sale_value}")
            return None

        # Calculate percentage change from sale date to effective date
        adjustment = ((effective_value - sale_value) / sale_value) * 100
        return round(float(adjustment), 4)

    except Exception as e:
        logger.error(f"Error calculating monthly adjustment for {metric}: {e}")
        return None


def prepare_trendline_data(monthly_data: List[Dict], metric: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prepare data for trendline analysis by converting dates to ordinal numbers.

    Args:
        monthly_data: List of monthly aggregation dictionaries
        metric: Either 'median_close' or 'median_pps'

    Returns:
        Tuple of (x_values, y_values) as numpy arrays
    """
    valid_data = []

    for month in monthly_data:
        year_month = month.get('year_month')
        value = month.get(metric)

        if year_month and value is not None and value > 0:
            try:
                # Convert YYYY-MM to datetime and then to ordinal
                dt = datetime.strptime(year_month, '%Y-%m')
                ordinal = dt.toordinal()
                valid_data.append((ordinal, float(value)))
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid month data: {year_month}, {value} - {e}")
                continue

    if len(valid_data) < 2:
        logger.warning(f"Insufficient data points for trendline analysis: {len(valid_data)}")
        return np.array([]), np.array([])

    # Sort by date
    valid_data.sort(key=lambda x: x[0])

    x_values = np.array([point[0] for point in valid_data])
    y_values = np.array([point[1] for point in valid_data])

    return x_values, y_values


def calculate_linear_trendline_adjustment(
    monthly_data: List[Dict],
    effective_date: date,
    sale_date: date,
    metric: str = 'median_close'
) -> Optional[float]:
    """
    Calculate time adjustment using linear regression trendline.

    Fits a linear trendline to the historical monthly data and calculates
    the percentage difference between the trendline values at the sale date
    and effective date.

    Args:
        monthly_data: List of monthly aggregation dictionaries
        effective_date: The appraisal effective date
        sale_date: The comparable sale date
        metric: Either 'median_close' or 'median_pps'

    Returns:
        Percentage adjustment (positive means increase from sale to effective date)
    """
    try:
        x_values, y_values = prepare_trendline_data(monthly_data, metric)

        if len(x_values) < 2:
            logger.warning(f"Insufficient data for linear trendline: {len(x_values)} points")
            return None

        # Perform linear regression
        coefficients = np.polyfit(x_values, y_values, 1)
        slope, intercept = coefficients

        # Convert dates to ordinals
        effective_ordinal = effective_date.toordinal()
        sale_ordinal = sale_date.toordinal()

        # Calculate trendline values
        effective_value = slope * effective_ordinal + intercept
        sale_value = slope * sale_ordinal + intercept

        if sale_value <= 0:
            logger.warning(f"Invalid sale value from trendline: {sale_value}")
            return None

        # Calculate percentage adjustment
        adjustment = ((effective_value - sale_value) / sale_value) * 100
        return round(float(adjustment), 4)

    except Exception as e:
        logger.error(f"Error calculating linear trendline adjustment for {metric}: {e}")
        return None


def calculate_polynomial_trendline_adjustment(
    monthly_data: List[Dict],
    effective_date: date,
    sale_date: date,
    metric: str = 'median_close',
    degree: int = 4
) -> Optional[float]:
    """
    Calculate time adjustment using polynomial regression trendline.

    Fits a polynomial trendline to the historical monthly data and calculates
    the percentage difference between the trendline values at the sale date
    and effective date.

    Args:
        monthly_data: List of monthly aggregation dictionaries
        effective_date: The appraisal effective date
        sale_date: The comparable sale date
        metric: Either 'median_close' or 'median_pps'
        degree: Polynomial degree (default 4)

    Returns:
        Percentage adjustment (positive means increase from sale to effective date)
    """
    try:
        x_values, y_values = prepare_trendline_data(monthly_data, metric)

        if len(x_values) < degree + 1:
            logger.warning(f"Insufficient data for degree {degree} polynomial: {len(x_values)} points needed {degree + 1}")
            return None

        # Perform polynomial regression
        coefficients = np.polyfit(x_values, y_values, degree)
        poly_function = np.poly1d(coefficients)

        # Convert dates to ordinals
        effective_ordinal = effective_date.toordinal()
        sale_ordinal = sale_date.toordinal()

        # Calculate polynomial values
        effective_value = poly_function(effective_ordinal)
        sale_value = poly_function(sale_ordinal)

        if sale_value <= 0:
            logger.warning(f"Invalid sale value from polynomial: {sale_value}")
            return None

        # Calculate percentage adjustment
        adjustment = ((effective_value - sale_value) / sale_value) * 100
        return round(float(adjustment), 4)

    except Exception as e:
        logger.error(f"Error calculating polynomial trendline adjustment for {metric}: {e}")
        return None


def process_time_adjustments(
    upload_results: Dict,
    effective_date: date,
    comparable_sales: List[Tuple[date, float, Optional[int], Optional[str]]]
) -> List[Dict]:
    """
    Process time adjustments for multiple comparable sales using all methodologies.

    Args:
        upload_results: Results summary from Upload model containing monthly_table
        effective_date: The appraisal effective date
        comparable_sales: List of tuples (sale_date, sale_price, square_footage, address)

    Returns:
        List of dictionaries containing adjustment results for each comparable
    """
    monthly_data = upload_results.get('monthly_table', [])

    if not monthly_data:
        logger.error("No monthly data available for time adjustment calculations")
        return []

    results = []

    for i, (sale_date, sale_price, square_footage, address) in enumerate(comparable_sales):
        try:
            result = {
                'comparable_index': i,
                'sale_date': sale_date.isoformat(),
                'sale_price': float(sale_price),
                'square_footage': square_footage,
                'address': address or f"Comparable {i + 1}",
                'effective_date': effective_date.isoformat(),
                'adjustments': {}
            }

            # Monthly median adjustments
            result['adjustments']['monthly_price'] = calculate_monthly_adjustment(
                monthly_data, effective_date, sale_date, 'median_close'
            )
            result['adjustments']['monthly_psf'] = calculate_monthly_adjustment(
                monthly_data, effective_date, sale_date, 'median_pps'
            )

            # Linear trendline adjustments
            result['adjustments']['linear_price'] = calculate_linear_trendline_adjustment(
                monthly_data, effective_date, sale_date, 'median_close'
            )
            result['adjustments']['linear_psf'] = calculate_linear_trendline_adjustment(
                monthly_data, effective_date, sale_date, 'median_pps'
            )

            # Polynomial trendline adjustments
            result['adjustments']['polynomial_price'] = calculate_polynomial_trendline_adjustment(
                monthly_data, effective_date, sale_date, 'median_close'
            )
            result['adjustments']['polynomial_psf'] = calculate_polynomial_trendline_adjustment(
                monthly_data, effective_date, sale_date, 'median_pps'
            )

            results.append(result)

        except Exception as e:
            logger.error(f"Error processing comparable {i}: {e}")
            continue

    return results


def generate_trendline_data(monthly_data: List[Dict], metric: str, num_points: int = 100) -> Dict:
    """
    Generate smooth trendline data for charting purposes.

    Args:
        monthly_data: List of monthly aggregation dictionaries
        metric: Either 'median_close' or 'median_pps'
        num_points: Number of points to generate for smooth curve

    Returns:
        Dictionary with linear and polynomial trendline data
    """
    try:
        x_values, y_values = prepare_trendline_data(monthly_data, metric)

        if len(x_values) < 2:
            return {'linear': [], 'polynomial': []}

        # Generate smooth x values across the data range
        x_min, x_max = x_values.min(), x_values.max()
        x_smooth = np.linspace(x_min, x_max, num_points)

        # Convert ordinals back to date strings for charting
        dates_smooth = [datetime.fromordinal(int(x)).strftime('%Y-%m') for x in x_smooth]

        # Linear trendline
        linear_coeffs = np.polyfit(x_values, y_values, 1)
        linear_values = np.polyval(linear_coeffs, x_smooth)

        # Polynomial trendline (use degree 4 if enough data)
        poly_degree = min(4, len(x_values) - 1)
        poly_coeffs = np.polyfit(x_values, y_values, poly_degree)
        poly_values = np.polyval(poly_coeffs, x_smooth)

        return {
            'linear': [{'x': dates_smooth[i], 'y': float(linear_values[i])} for i in range(len(dates_smooth))],
            'polynomial': [{'x': dates_smooth[i], 'y': float(poly_values[i])} for i in range(len(dates_smooth))]
        }

    except Exception as e:
        logger.error(f"Error generating trendline data for {metric}: {e}")
        return {'linear': [], 'polynomial': []}