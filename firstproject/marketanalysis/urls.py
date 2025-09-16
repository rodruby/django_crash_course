from django.urls import path
from . import views

app_name = 'marketanalysis'

urlpatterns = [
    # Main dashboard and list views
    path('', views.AnalysisListView.as_view(), name='analysis_list'),
    path('upload/', views.UploadCreateView.as_view(), name='upload'),

    # Analysis detail views
    path('analysis/<int:pk>/', views.AnalysisDetailView.as_view(), name='view_analysis'),

    # Time adjustment views
    path('analysis/<int:pk>/time-adjustment/', views.TimeAdjustmentCreateView.as_view(), name='time_adjustment'),
    path('time-adjustment/<int:pk>/', views.TimeAdjustmentDetailView.as_view(), name='time_adjustment_detail'),

    # Legacy/utility views
    path('hello/', views.hello, name='hello'),
]
