from django.shortcuts import render
from rest_framework.decorators import api_view
from .models import Product,Cart,CartItem
from .serializers import ProductSerializer,DetailedProductSerializer,CartItemSerializer
from rest_framework.response import Response



@api_view(['GET'])
def products(request):
    products=Product.objects.all()
    serializer=ProductSerializer(products,many=True)
    return Response(serializer.data)


@api_view(['GET'])
def product_detail(request,slug):
    product=Product.objects.get(slug=slug)
    serializer=DetailedProductSerializer(product)
    return Response(serializer.data)

@api_view(['POST'])
def add_item(request):
    try:
        cart_code=request.data.get('cart_code')
        product_id=request.data.get('product_id')
        
        cart,created=Cart.objects.get_or_create(cart_code=cart_code)
        product=product.objects.get(id=product_id)
        
        cartitem,created=CartItem.objects.get_or_create(cart=cart,product=product)
        cartitem.quantity=1
        cartitem.save()
        
        serialezer=CartItemSerializer(cartitem)
        
        return Response({'data':serialezer.data,'message':'cartitem created succesfully'},status=201)
    
    except Exception as e:
        return Response({'error':str(e)},status=400)
     
