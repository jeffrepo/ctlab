from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    overdue_authorization_required = fields.Boolean(
        string="Requiere autorización por vencidos",
        copy=False,
        readonly=True,
        tracking=True,
    )
    overdue_authorized = fields.Boolean(
        string="Autorizada por vencidos",
        copy=False,
        readonly=True,
        tracking=True,
    )
    overdue_authorized_by_id = fields.Many2one(
        "res.users",
        string="Autorizada por",
        copy=False,
        readonly=True,
        tracking=True,
    )
    overdue_authorized_date = fields.Datetime(
        string="Fecha de autorización",
        copy=False,
        readonly=True,
        tracking=True,
    )

    def action_post(self):
        for move in self:
            if move._requires_overdue_authorization_before_posting():
                overdue_invoices = move._get_overdue_unpaid_customer_invoices()
                if overdue_invoices:
                    move._request_overdue_authorization(overdue_invoices)
                    return move._overdue_authorization_notification_action()
        return super().action_post()

    def _overdue_authorization_notification_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "warning",
                "sticky": True,
                "title": _("Facturas vencidas pendientes de autorización"),
                "message": _(
                    "El cliente %(partner)s tiene facturas vencidas sin pagar. "
                    "Un autorizador de facturas debe aprobar esta factura antes "
                    "de confirmarla."
                )
                % {"partner": self.partner_id.display_name},
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    def action_authorize_overdue_invoice(self):
        self.ensure_one()
        if not self.env.user.has_group(
            "account_invoice_overdue_authorization.group_invoice_authorizer"
        ):
            raise UserError(_("Solo los autorizadores pueden autorizar esta factura."))
        if self.state != "draft":
            raise UserError(_("Solo se pueden autorizar facturas en borrador."))
        if not self.overdue_authorization_required:
            raise UserError(_("Esta factura no requiere autorización por vencidos."))

        self.write(
            {
                "overdue_authorized": True,
                "overdue_authorized_by_id": self.env.user.id,
                "overdue_authorized_date": fields.Datetime.now(),
            }
        )
        self._notify_invoice_creator_authorized()
        self.message_post(
            body=Markup("<p>%s</p>")
            % _("La factura fue autorizada por %s y ya puede confirmarse.")
            % self.env.user.display_name,
            subtype_xmlid="mail.mt_note",
        )
        return True

    def write(self, vals):
        reset_fields = {"partner_id", "commercial_partner_id", "company_id", "move_type"}
        should_reset_authorization = bool(reset_fields.intersection(vals))
        if should_reset_authorization:
            vals = dict(vals)
            vals.update(
                {
                    "overdue_authorization_required": False,
                    "overdue_authorized": False,
                    "overdue_authorized_by_id": False,
                    "overdue_authorized_date": False,
                }
            )
        return super().write(vals)

    def _requires_overdue_authorization_before_posting(self):
        self.ensure_one()
        return (
            self.is_invoice(include_receipts=False)
            and self.move_type == "out_invoice"
            and self.state == "draft"
            and self.partner_id
            and not self.overdue_authorized
        )

    def _get_overdue_unpaid_customer_invoices(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        commercial_partner = self.partner_id.commercial_partner_id
        domain = [
            ("id", "!=", self.id),
            ("company_id", "=", self.company_id.id),
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("commercial_partner_id", "=", commercial_partner.id),
            ("invoice_date_due", "<", today),
            ("amount_residual", ">", 0.0),
            ("payment_state", "not in", ["paid", "in_payment", "reversed"]),
        ]
        return self.search(domain, order="invoice_date_due asc, name asc")

    def _request_overdue_authorization(self, overdue_invoices):
        self.ensure_one()
        self.overdue_authorization_required = True
        authorizer_partners = self._get_invoice_authorizer_partners()
        overdue_invoice_names = ", ".join(
            "%s - %s" % (invoice.display_name, invoice.invoice_date_due or "")
            for invoice in overdue_invoices[:10]
        )
        extra_count = max(len(overdue_invoices) - 10, 0)
        extra_message = (
            Markup("<p>%s</p>")
            % _("Existen %s facturas vencidas adicionales.")
            % extra_count
            if extra_count
            else Markup("")
        )
        body = Markup("<p>%s</p><p>%s</p>%s") % (
            _(
                "Se requiere autorización antes de confirmar esta factura "
                "porque el cliente tiene facturas vencidas sin pagar:"
            ),
            overdue_invoice_names,
            extra_message,
        )
        self.message_post(
            body=body,
            partner_ids=authorizer_partners.ids,
            subtype_xmlid="mail.mt_note",
        )

    def _get_invoice_authorizer_partners(self):
        group = self.env.ref(
            "account_invoice_overdue_authorization.group_invoice_authorizer",
            raise_if_not_found=False,
        )
        if not group:
            return self.env["res.partner"]
        return group.users.filtered(lambda user: user.active).partner_id

    def _notify_invoice_creator_authorized(self):
        self.ensure_one()
        creator_partner = self.create_uid.partner_id
        if not creator_partner:
            return
        self.message_post(
            body=Markup("<p>%s</p>")
            % _("Tu factura fue autorizada por %s. Ya puedes confirmarla.")
            % self.env.user.display_name,
            partner_ids=creator_partner.ids,
            subtype_xmlid="mail.mt_note",
        )
