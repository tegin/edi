# Copyright 2021 Creu Blanca
# @author: Enric Tobella
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, fields
from odoo.exceptions import ValidationError
from odoo.tests.common import Form
from odoo.tools.float_utils import float_compare
from odoo.tools.misc import format_amount

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class EdiInputPdf2DataProcess(Component):
    _name = "edi.input.process.pdf2data"
    _inherit = "edi.input.process.pdf2data.abstract"
    _exchange_type = "pdf2data_account_move"

    def process_data(self, data, template):
        partner = self._get_partner(data, template)
        company = self._get_company(data, template) or self.env.company
        if not partner:
            raise ValidationError(_("Partner cannot be found"))
        invoice = Form(
            self.env["account.move"].with_context(
                default_company_id=company.id, default_type="in_invoice",
            )
        )
        invoice.partner_id = partner
        if data.get("date"):
            invoice.invoice_date = fields.Datetime.from_string(data.get("date"))
        mode = template.exchange_type_id.advanced_settings.get(
            "account_move_import_mode", []
        )
        if hasattr(self, "_modify_form_move_%s" % mode):
            getattr(self, "_modify_form_move_%s" % mode)(invoice, data, template)
        invoice = invoice.save()
        # This fields are done after the save of form in order to ensure that
        # all works as expected
        if data.get("invoice_number", False):
            invoice.ref = data["invoice_number"]
            invoice.invoice_payment_ref = data["invoice_number"]
        if data.get("due_date"):
            invoice.invoice_payment_term_id = self.env["account.payment.term"]
            invoice.invoice_date_due = fields.Datetime.from_string(data.get("due_date"))
        if hasattr(self, "_modify_move_%s" % mode):
            getattr(self, "_modify_move_%s" % mode)(invoice, data, template)
        invoice.flush()
        self._validate_invoice(invoice, data, template)
        self.exchange_record.write({"model": invoice._name, "res_id": invoice.id})

    def _validate_invoice(self, invoice, data, template):
        errors = []
        if data.get("amount"):
            if float_compare(
                data.get("amount"),
                invoice.amount_total,
                precision_rounding=invoice.currency_id.rounding,
            ):
                errors.append(
                    _("Total Amount has a difference of %s")
                    % format_amount(
                        self.env,
                        invoice.currency_id.round(
                            data.get("amount") - invoice.amount_total
                        ),
                        invoice.currency_id,
                        self.env.user.lang,
                    )
                )
        message = [_("Invoice has been imported from a file import.")]
        if errors:
            message.append(_("<b>Some issues have been detected</b>"))
            message += errors
        invoice.message_post(
            body="<br/>".join(message),
            attachments=[
                (
                    self.exchange_record.exchange_filename,
                    self.exchange_record.exchange_file,
                )
            ],
        )

    def _modify_form_move_line(self, invoice, data, template):
        for line_data in data["lines"]:
            with invoice.invoice_line_ids.new() as line_form:
                product = self._get_product(line_data, template, invoice.partner_id)
                if product:
                    line_form.product_id = product
                if line_data.get("description"):
                    line_form.name = line_data.get("description")
                line_form.quantity = line_data.get("qty", 1)
                if line_data.get("price_unit"):
                    line_form.price_unit = line_data.get("price_unit", 1)

    def _modify_form_move_fill_total(self, invoice, data, template):
        with invoice.invoice_line_ids.new() as line_form:
            product = self._get_product(data, template, invoice.partner_id)
            if product:
                line_form.product_id = product
            if data.get("description"):
                line_form.name = data.get("description")
            line_form.quantity = 1
            line_form.price_unit = data["amount_untaxed"]

    def _modify_form_move_purchase(self, invoice, data, template):
        sources = data.get("source")
        if not isinstance(sources, list):
            sources = [sources]
        for source in sources:
            purchase = self.env["purchase.order"].search(
                [
                    ("partner_id", "=", invoice.partner_id.id),
                    ("partner_ref", "=", source),
                    ("company_id", "=", invoice.company_id.id),
                ],
                limit=1,
            )
            if purchase:
                invoice.purchase_id = purchase

    def _get_partner_domain(self, data, template):
        if data.get("partner_vat"):
            yield [("vat", "=", data["partner_vat"])]
        if data.get("partner_ref"):
            yield [("ref", "=", data["partner_ref"])]
        if data.get("partner_id"):
            yield [("id", "=", data["partner_id"])]

    def _get_partner(self, data, template):
        partner = self.env["res.partner"]
        for domain in self._get_partner_domain(data, template):
            partner = partner.search(domain, limit=1)
            if partner:
                return partner
        return partner

    def _get_company(self, data, template):
        company = self.env["res.company"]
        if data.get("company_vat"):
            company = company.search([("vat", "=", data["company_vat"])], limit=1)
            if company:
                return company
        return company

    def _get_product_domain(self, data, template):
        if data.get("product_code"):
            yield [("default_code", "=", data.get("product_code"))]

    def _get_product_seller_domain(self, data, template, partner):
        if data.get("product_code"):
            yield [
                ("product_code", "=", data.get("product_code")),
                ("name", "=", partner.id),
            ]

    def _get_product(self, data, template, partner=False):
        product = self.env["product.product"]
        for domain in self._get_product_domain(data, template):
            product = product.search(domain)
            if product:
                return product
        if partner:
            for domain in self._get_product_seller_domain(
                data, template, partner=partner
            ):
                seller = self.env["product.supplierinfo"].search(domain, limit=1)
                if seller:
                    return (
                        seller.product_id
                        or seller.product_tmpl_id.product_variant_ids[0]
                    )

        return product
