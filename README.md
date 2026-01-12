# 📦 M&M Hogar - Sistema de Registro de Salidas

Sistema web para registrar y gestionar salidas de mercadería en M&M Hogar. Permite cargar productos, registrar ventas por canal, y visualizar estadísticas en tiempo real.

## ✨ Características

- ✅ **Gestión de Productos**: Cargar, editar y eliminar productos con SKU y variantes
- ✅ **Registro de Salidas**: Interfaz rápida para registrar vendidas y canal
- ✅ **Multi-usuario**: 3+ usuarios pueden registrar simultáneamente
- ✅ **Estadísticas Reales**: Gráficos y tablas en tiempo real
- ✅ **Múltiples Canales**: Marketplace 1, Marketplace 2, Web, Directo, etc.
- ✅ **Exportación**: Descargar datos en CSV
- ✅ **Responsive**: Funciona en PC, tablet y celular

## 🚀 Cómo Usar

### 1️⃣ Cargar Productos
- Ve a la pestaña **"📥 Cargar Productos"**
- Completa: SKU, Nombre, Variante, Categoría (opcional)
- Haz clic en **"✅ Guardar Producto"**

### 2️⃣ Registrar Salidas
- Ve a la pestaña **"📊 Registrar Salidas"**
- Ingresa tu nombre de usuario (en la barra lateral)
- Busca el producto vendido
- Ingresa la cantidad
- Selecciona el canal de venta
- Haz clic en **"💾 Guardar Salida"**

### 3️⃣ Ver Estadísticas
- Ve a la pestaña **"📈 Estadísticas"**
- Selecciona el período (Hoy, Última Semana, Este Mes, Personalizado)
- Visualiza gráficos de ventas por canal y productos top

### 4️⃣ Historial Completo
- Ve a la pestaña **"📋 Historial"**
- Filtra por canal y usuario si lo deseas
- Descarga como CSV para análisis posterior

## 🌐 Acceso Online

La app está desplegada en Streamlit Cloud:

https://mmhogar-salidas.streamlit.app


Simplemente abre este link en cualquier navegador (PC, celular, tablet) y comienza a usar.

## 📊 Base de Datos (Supabase)

La app usa Supabase (PostgreSQL) para almacenar:
- **Tabla `productos`**: SKU, nombre, variante, categoría
- **Tabla `salidas`**: producto vendido, cantidad, canal, usuario, fecha

Los datos se sincronizan en tiempo real entre los 3 usuarios.

## 🔄 Sincronización Multi-usuario

- Los cambios en cualquier dispositivo se actualizan automáticamente
- Todos los usuarios ven los mismos datos en tiempo real
- Funciona incluso con múltiples conexiones simultáneas

## 📱 Compatibilidad

- ✅ Windows, Mac, Linux (navegador)
- ✅ iPhone, iPad (Safari)
- ✅ Android (Chrome)
- ✅ Tablets

## 🚧 Próximas Fases

**Fase 2**: Integración con Sistema de Inventario
**Fase 3**: Sistema de Inventario Completo

## 📞 Soporte

Para reportar bugs o sugerencias, contacta al desarrollador.

---

**Versión**: 1.0  
**Última actualización**: Enero 2026  
**Autor**: M&M Hogar Team
