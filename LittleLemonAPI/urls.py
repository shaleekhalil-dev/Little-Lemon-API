from django.urls import path
from . import views

urlpatterns = [
    path('categories', views.CategoriesView.as_view()),
    path('menu-items', views.MenuItemsView.as_view()),
    path('menu-items/<int:pk>', views.SingleMenuItemView.as_view()),
    
    # Path for managing managers group
    path('groups/manager/users', views.managers),
    
    # Path for managing delivery crew group
    path('groups/delivery-crew/users', views.delivery_crew),
    
    # Path for shopping cart management
    path('cart/menu-items', views.CartView.as_view()),

    # Path for order management (List and Create)
    path('orders', views.OrdersView.as_view()),
    
    # Path for single order management (Retrieve, Update, Delete)
    path('orders/<int:pk>', views.SingleOrderView.as_view()),
]