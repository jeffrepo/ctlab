# Customer Invoice Overdue Authorization

Módulo para Odoo 18 que bloquea la confirmación de facturas de cliente cuando el cliente tiene facturas vencidas, publicadas y pendientes de pago.

## Comportamiento principal

- Los usuarios pueden crear facturas de cliente en borrador normalmente.
- Cuando un usuario intenta confirmar/publicar una factura de cliente en borrador, el módulo valida si el contacto comercial tiene facturas de cliente vencidas y no pagadas en la misma compañía.
- Si existen facturas vencidas, la factura permanece en borrador, se envía una nota interna en el chatter a los usuarios del grupo **Usuario autorizador facturas** y Odoo muestra una notificación de advertencia al usuario.
- Los usuarios del grupo **Usuario autorizador facturas** pueden ver el botón **Autorizar** en la factura en borrador después de que se solicita autorización.
- Al autorizarse, el creador de la factura recibe una notificación interna en el chatter y la factura ya puede confirmarse.

## Criterio de vencimiento

Una factura vencida es una factura de cliente publicada del mismo contacto comercial y compañía donde:

- `invoice_date_due` es anterior a hoy;
- `amount_residual` es mayor que cero;
- `payment_state` no es pagado, en pago, ni reversado.
