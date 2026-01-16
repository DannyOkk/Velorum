from django.contrib import admin
from .models import *

# Register your models here.

admin.site.register(Product)
admin.site.register(OrderDetail)
admin.site.register(Pay)
admin.site.register(Category)
admin.site.register(Shipment)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'get_nombre_cliente', 'get_email_cliente', 'fecha', 'total', 'estado', 'metodo_pago')
    list_filter = ('estado', 'fecha', 'metodo_pago')
    search_fields = ('id', 'usuario__username', 'email_invitado', 'nombre_invitado', 'apellido_invitado', 'dni_invitado')
    readonly_fields = ('fecha', 'total')
    
    fieldsets = (
        ('Cliente', {
            'fields': ('usuario', 'nombre_invitado', 'apellido_invitado', 'email_invitado', 'telefono_invitado', 'dni_invitado')
        }),
        ('Pedido', {
            'fields': ('estado', 'total', 'fecha', 'metodo_pago')
        }),
        ('Envío', {
            'fields': ('direccion_envio', 'codigo_postal', 'zona_envio', 'costo_envio')
        }),
    )
    
    def get_nombre_cliente(self, obj):
        if obj.usuario:
            return f"{obj.usuario.first_name} {obj.usuario.last_name}".strip() or obj.usuario.username
        return f"{obj.nombre_invitado or ''} {obj.apellido_invitado or ''}".strip() or 'Invitado'
    get_nombre_cliente.short_description = 'Nombre'
    
    def get_email_cliente(self, obj):
        if obj.usuario:
            return obj.usuario.email
        return obj.email_invitado or 'N/A'
    get_email_cliente.short_description = 'Email'

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'product__nombre', 'product__name')


@admin.register(CodigoDescuento)
class CodigoDescuentoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'porcentaje_descuento', 'activo', 'usos_actuales', 'usos_maximos', 'fecha_expiracion')
    list_filter = ('activo', 'fecha_creacion', 'fecha_expiracion')
    search_fields = ('codigo', 'descripcion')
    readonly_fields = ('usos_actuales', 'fecha_creacion', 'fecha_actualizacion')
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'descripcion', 'porcentaje_descuento')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_inicio', 'fecha_expiracion')
        }),
        ('Límites', {
            'fields': ('usos_maximos', 'usos_actuales', 'usos_por_usuario', 'monto_minimo')
        }),
        ('Metadata', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UsoCodigoDescuento)
class UsoCodigoDescuentoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'orden', 'usuario', 'monto_descuento', 'fecha_uso')
    list_filter = ('fecha_uso', 'codigo')
    search_fields = ('codigo__codigo', 'orden__id', 'usuario__username')
    readonly_fields = ('fecha_uso',)
    