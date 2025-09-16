# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

This is a Django crash course project with the main Django project located in `firstproject/`. The project contains two Django apps:

1. **firstapp** - A basic Django app demonstrating forms, models, and views with:
   - MenuItem model for restaurant menu items
   - Reservation model for table reservations
   - Contact model for contact form submissions
   - Function-based and class-based views
   - Template-based UI with forms

2. **marketanalysis** - A real estate market analysis app featuring:
   - Sale model for real estate transaction data
   - Upload model for tracking CSV file uploads and analysis results
   - CSV/Excel file upload and processing with pandas
   - Market trend analysis with time-based adjustments
   - Data visualization capabilities with plotly

## Key Commands

### Development Server
```bash
cd firstproject
python manage.py runserver
```

### Database Operations
```bash
cd firstproject
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser  # Create admin user
```

### Dependencies
```bash
cd firstproject
pip install -r requirements.txt
```

### Testing
```bash
cd firstproject
python manage.py test
```

## Configuration

- **Django Version**: 5.2.5
- **Database**: SQLite3 (development)
- **Python Dependencies**: Django, pandas, openpyxl, plotly, psycopg2-binary
- **Settings**: Located in `firstproject/firstproject/settings.py`
- **URLs**: Main URL configuration in `firstproject/firstproject/urls.py`

## URL Structure

- `/admin/` - Django admin interface
- `/firstapp/` - Restaurant app URLs (home, contact, reservations)
- `/market/` - Market analysis app URLs (upload, analysis views)

## Database Models

### firstapp
- `MenuItem`: Restaurant menu items with name and price
- `Reservation`: Table reservations with guest details and timing
- `Contact`: Contact form submissions with timestamps and metadata

### marketanalysis
- `Sale`: Real estate transaction records with MLS data, pricing, and property details
- `Upload`: File upload metadata with analysis results stored as JSON

## File Uploads

The marketanalysis app handles CSV/Excel file uploads in the `uploads/` directory. Files are processed using pandas for market trend analysis and can optionally save individual sale records to the database.

## Key Dependencies

- **pandas**: Data processing and analysis
- **openpyxl**: Excel file reading
- **plotly**: Data visualization (chart generation)
- **psycopg2-binary**: PostgreSQL adapter (if switching from SQLite)

## Development Notes

- Virtual environment setup recommended (`.venv/` directory exists)
- Database migrations are tracked in each app's `migrations/` folder
- Static files configured but no static directory currently exists
- Templates are organized per app in `app_name/templates/app_name/` structure
- Forms use Django's built-in form handling with validation