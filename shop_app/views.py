from django.shortcuts import render
from rest_framework.decorators import api_view,permission_classes
from .models import Product,Cart,CartItem,Transaction
from .serializers import ProductSerializer,DetailedProductSerializer,CartItemSerializer,SimpleCartSerializer,CartSerializer,UserSerializer
from rest_framework.response import Response
from core.models import CustomUser
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
from django.conf import settings
from rest_framework import status
import uuid
import requests
import paypalrestsdk

BASE_URL=settings.REACT_BASE_URL

paypalrestsdk.configure({
    'mode':settings.PAYPAL_MODE,
    'client_id':settings.PAYPAL_CLIENT_ID,
    'client_secret':settings.PAYPAL_CLIENT_SECRET
})


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
        
        #user=CustomUser.objects.get(id=1)
        #user=request.user
        cart,created=Cart.objects.get_or_create(cart_code=cart_code) #QUITAR USER ID CUANDO SE HAGA EL LOGIN
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
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
            currency='NGN'
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
                'Content-Type': 'application/json'
            }
            
            response=requests.post(
                'https://api.flutterwave.com/v3/payments',
                json=flutterwave_payload,
                headers=headers
            )
            
            if response.status_code==200:
                return Response(response.json(),status=status.HTTP_200_OK)
            else:
                return Response(response.json(),status=response.status_code)
            
        except requests.exceptions.RequestException as e:
            return Response({'error':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    
@api_view(['POST'])
def payment_callback(request):
    status=request.GET.get('status')
    tx_ref=request.GET.get('tx_ref')
    transaction_id=request.GET.get('transaction_id')
    user=request.user
    
    
    if status == 'successful':
        headers={
            'Authorization':f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
            
        }
        
        response=requests.get(
            f'https://api.flutterwave.com/v3/transactions/{transaction_id}/verify',
            headers=headers
                              
                              )
        
        response_data=response.json()
        print(response_data)
        
        if response_data['status']=='success':
            transaction=Transaction.objects.get(ref=tx_ref)
            if(response_data['data']['status']=='successful'
               and float(response_data['data']['amount']==float(transaction.amount))
               and response_data['data']['currency']==transaction.currency
               ):
                
                transaction.status='completed'
                transaction.save()
                
                cart=transaction.cart
                cart.paid=True
                cart.user=user
                cart.save()
                
                return Response({'message':'payment successful!','subMessage':'you have successfully made payment'})
            else:
                return Response({'message':'Payment verification failed','subMessage':'your payment virification failed'})
            
        else:
            return Response({'message':'Failed to verify transaction with flutterwave','subMessge':'we cound not to verify transaction with flutterwave'})
            
    
    else:
        return Response({'message':'Payment was not successful'},status=400)    


@api_view(['POST'])
def initiate_paypal_payment(request):
    if request.method == 'POST' and request.user.is_authenticated:
        tx_ref=str(uuid.uuid4())
        user=request.user
        cart_code=request.data.get('cart_code')
        cart= Cart.objects.get(cart_code=cart_code)
        amount=sum(item.product.price * item.quantity for item in cart.items.all())
        tax= Decimal('4.00')
        total_amount=amount + tax
        
        payment=paypalrestsdk.Payment({
            'intent':'sale',
            'payer':{
              'payment_method':'paypal'  
            },
            'redirect_urls':{
                'return_url':f'{BASE_URL}/payment-status?paymentStatus=success&ref={tx_ref}',
                'cancel_url':f'{BASE_URL}/payment-status?paymentStatus=cancel'
            },
            'transactions':[{
                'item_list':{
                    'items':[{
                        'name':'cart Items',
                        'sku':'cart',
                        'price':str(total_amount),
                        'currency':'USD',
                        'quantity':1
                    }]
                },
                
                'amount':{
                    'total':str(total_amount),
                    'currency':'USD'
                },
                'description':'Payment for cart items.'
            }]
        
            
        })
        
        print(payment)
        
        transaction,created=Transaction.objects.get_or_create(
            ref=tx_ref,
            cart=cart,
            amount=total_amount,
            user=user,
            status='pending'
        )
       
        if payment.create():
           for link in payment.links:
               if link.rel=='approval_url':
                   approval_url=str(link.href)
                   return Response({'approval_url':approval_url})
        else:
            return Response({'error':payment.error},status=400) 
    
    return Response({'error':'Invalid request'},status=400)
        

@api_view(['POST'])
def paypal_payment_callback(request):
    payment_id=request.query_params.get('paymentId')
    payer_id=request.query_params.get('PayerID')
    ref=request.query_params.get('ref')
    
    user=request.user
    
    print('refff: ',ref)
    
    transaction=Transaction.objects.get(ref=ref)
    
    if payment_id and payer_id:
        
        payment= paypalrestsdk.Payment.find(payment_id)
        
        transaction.status='completed'
        transaction.save()
        cart=transaction.cart
        cart.paid=True
        cart.user=user
        cart.save()
        
        return Response({'message':'Payment successful!','subMessage':'you have successfully made payment for the items you purchase'},status=200)
    else:
        return Response({'error':'Invalid payment details'},status=400)
    

