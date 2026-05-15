"""
URL configuration for shop app
"""
from django.urls import path
from shop.views.brands import (
    BrandListView, BrandCreateView, BrandUploadMediaView, BrandProductsGroupedView
)
from shop.views.groups import (
    GroupListView, GroupTreeView, GroupCreateView, GroupUploadMediaView, GroupWithProductsView
)
from shop.views.products import (
    ProductListView, ProductCreateView, ProductDetailView, ProductUpdateView, ProductFilterView
)
from shop.views.attributes import (
    CharacteristicListView, ProductAttributesView, ProductAttributeCreateView
)
from shop.views.media import ProductMediaListView, ProductMediaUploadView
from shop.views.documents import ProductDocumentListView, ProductDocumentUploadView
from shop.views.product_certificates import ProductCertificateListView, ProductCertificateUploadView
from shop.views.news import NewsListView, NewsCreateView
from shop.views.serts import SertListView
from shop.views.slider import SliderListView
from shop.views.inquiries import InquiryCreateView
from shop.views.filters import GroupFiltersView, GlobalFiltersView
from shop.views.search import GlobalSearchView
from shop.views.catalog import CatalogResultsView, CatalogFacetsView
from shop.views.public_orders import PublicOrderCreateView
from shop.views.html_content import HtmlContentView
from shop.views.contacts import ContactInfoView
from shop.views.cities import CityListView
from shop.views.agents import AgentListView

urlpatterns = [
    path('cities', CityListView.as_view(), name='cities-list'),
    # Brands
    path('brands', BrandListView.as_view(), name='brands-list'),
    path('brands', BrandCreateView.as_view(), name='brands-create'),
    path('brands/<int:brand_id>/upload-media', BrandUploadMediaView.as_view(), name='brands-upload-media'),
    path('brands/<str:brand_identifier>', BrandProductsGroupedView.as_view(), name='brands-detail'),
    
    # Groups
    path('groups', GroupListView.as_view(), name='groups-list'),
    path('groups', GroupCreateView.as_view(), name='groups-create'),
    path('groups/tree', GroupTreeView.as_view(), name='groups-tree'),
    path('groups/<int:group_id>/upload-media', GroupUploadMediaView.as_view(), name='groups-upload-media'),
    path('groups/<str:group_identifier>', GroupWithProductsView.as_view(), name='groups-detail'),
    
    # Products
    path('products', ProductListView.as_view(), name='products-list'),
    path('products/filter', ProductFilterView.as_view(), name='products-filter'),
    path('products', ProductCreateView.as_view(), name='products-create'),
    path('products/<int:product_id>', ProductDetailView.as_view(), name='products-detail'),
    path('products/<int:product_id>', ProductUpdateView.as_view(), name='products-update'),
    
    # Attributes
    path('groups/<int:group_id>/characteristics', CharacteristicListView.as_view(), name='characteristics-list'),
    path('products/<int:product_id>/attributes', ProductAttributesView.as_view(), name='product-attributes'),
    path('products/<int:product_id>/attributes', ProductAttributeCreateView.as_view(), name='product-attributes-create'),
    
    # Media
    path('products/<int:product_id>/media', ProductMediaListView.as_view(), name='product-media-list'),
    path('products/<int:product_id>/media', ProductMediaUploadView.as_view(), name='product-media-upload'),
    path('products/<int:product_id>/documents', ProductDocumentListView.as_view(), name='product-document-list'),
    path('products/<int:product_id>/documents/upload', ProductDocumentUploadView.as_view(), name='product-document-upload'),
    path('products/<int:product_id>/certificates', ProductCertificateListView.as_view(), name='product-certificate-list'),
    path('products/<int:product_id>/certificates/upload', ProductCertificateUploadView.as_view(), name='product-certificate-upload'),
    
    # News
    path('news', NewsListView.as_view(), name='news-list'),
    path('news', NewsCreateView.as_view(), name='news-create'),
    path('slider', SliderListView.as_view(), name='slider-list'),
    path('serts', SertListView.as_view(), name='sert-list'),
    path('inquiries', InquiryCreateView.as_view(), name='inquiry-create'),
    path('public-orders', PublicOrderCreateView.as_view(), name='public-order-create'),
    path('html-content', HtmlContentView.as_view(), name='html-content'),
    path('contacts', ContactInfoView.as_view(), name='contact-info'),
    path('agents', AgentListView.as_view(), name='agents-list'),
    
    # Filters
    path('groups/<int:group_id>/filters', GroupFiltersView.as_view(), name='group-filters'),
    path('products/filters', GlobalFiltersView.as_view(), name='global-filters'),
    path('search', GlobalSearchView.as_view(), name='global-search'),
    path('catalog/results', CatalogResultsView.as_view(), name='catalog-results'),
    path('catalog/facets', CatalogFacetsView.as_view(), name='catalog-facets'),
]
