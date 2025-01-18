from django.shortcuts import render
from rest_framework.decorators import api_view,permission_classes
from .models import Product,Cart,CartItem,Transaction
from .serializers import ProductSerializer,DetailedProductSerializer,CartItemSerializer,SimpleCartSerializer,CartSerializer,UserSerializer
from rest_framework.response import Response
from core.models import CustomUser
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
from django.conf import settings
import uuid
BASE_URL='http://localhost:5173'


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
        
        user=CustomUser.objects.get(id=1)
        cart,created=Cart.objects.get_or_create(cart_code=cart_code,user=user) #QUITAR USER ID CUANDO SE HAGA EL LOGIN
        print(created)
        product=Product.objects.get(id=product_id)
        
        cartitem,created=CartItem.objects.get_or_create(cart=cart,product=product)
        cartitem.quantity=1
        cartitem.save()
        
        serialezer=CartItemSerializer(cartitem)
        
        return Response({'data':serialezer.data,'message':'cartitem created succesfully'},status=201)
    
    except Exception as e:
        return Response({'error':str(e)},status=400)
    
@api_view(['GET'])
def product_in_cart(request):
    cart_code=request.query_params.get('cart_code')
    product_id=request.query_params.get('product_id')
    try:
        cart=Cart.objects.get(cart_code=cart_code)
        product=Product.objects.get(id=product_id)
        product_exists_in_cart=CartItem.objects.filter(cart=cart, product=product).exists()
    except:
        product_exists_in_cart=False
    
    
    
   
    
    return Response({'product_in_cart':product_exists_in_cart})    
    
     
@api_view(['GET'])
def get_cart_stat(request):
    cart_code=request.query_params.get('cart_code')
    cart=Cart.objects.get(cart_code=cart_code,paid=False)
    serializer=SimpleCartSerializer(cart)
    return Response(serializer.data)

@api_view(['GET'])
def get_cart(request):
    cart_code=request.query_params.get('cart_code')
    cart=Cart.objects.get(cart_code=cart_code,paid=False)
    serializer=CartSerializer(cart)
    return Response(serializer.data)

@api_view(['PATCH'])
def update_quantity(request):
    try:
        cartitem_id= request.data.get('item_id')
        quantity=request.data.get('quantity')
        quantity=int(quantity)
        cartitem= CartItem.objects.get(id=cartitem_id)
        cartitem.quantity=quantity
        cartitem.save()
        serializer=CartItemSerializer(cartitem)
        return Response({'data':serializer.data, 'message':'Cartitem updated successfully'})
    
    except Exception as e:
        return Response({'error':str(e)},status=400)

@api_view(['POST'])
def delete_item(request):
    try:
        cartitem_id=request.data.get('item_id')
        cartitem=CartItem.objects.get(id=cartitem_id)
        cartitem.delete()
        return Response({'message':'product deleted successfully'},status=200)
    except Exception as e:
        return Response({'error':str(e)},status=400)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_username(request):
    user=request.user
    return Response({'username':user.username})
   

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    user=request.user
    serializer=UserSerializer(user)
    return Response(serializer.data)

def initiate_payment(request):
    if request.user:
        try:
            tx_ref=str(uuid.uuid4())
            cart_code=request.data.get('cart_code')
            cart=Cart.objects.get(cart_code=cart_code)
            user=request.user
            
            amount=sum([item.quantity * item.product.price for item in cart.items.all()])
            tax=Decimal('4.00')
            total_amount=amount + tax
            currency='COP'
            redirect_url=f'{BASE_URL}/payment-status/'
            
            transaction=Transaction.objects.create(
                ref=tx_ref,
                cart=cart,
                amount=total_amount,
                currency=currency,
                user=user,
                status='pending'
                
            )
            
            flutterwave_payload={
                'tx_ref':tx_ref,
                'amount':str(total_amount),
                'currency':currency,
                'redirect_url':redirect_url,
                'customer':{
                    'email':user.email,
                    'name':user.username,
                    'phonenumber':user.phone
                },
                'customizations':{
                    'title':'Shoppit Payment'
                }
            }
            
            headers={
                'Authorization':f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
                'Content-type': 'application/json'
            }
            