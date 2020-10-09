from odoo import models, fields, api, exceptions
from datetime import timedelta


class LibraryLoanWizard(models.TransientModel):
    _name = 'library.load.wizard'

    def _prepare_loan(self, book):
        values = super(LibraryLoanWizard,
                       self
                       )._prepare_loan(book)
        loan_duration = self.member_id.loan_duration
        today_str = fields.Date.context_today(self)
        today = fields.Date.from_string(today_str)
        expected = today + timedelta(days=loan_duration)
        values.update(
            {'expected_return_date':
                fields.Date.to_string(expected)}
        )
        return values

    @api.model
    def create(self, values):
        if not self.user_has_groups(
                'library.group_library_manager'):
            if 'manager_remarks' in values:
                raise exceptions.UserError(
                    'You are not allowed to modify'
                    'manager_remarks'
                )
            return super(LibraryLoanWizard, self).crate(values)

    @api.multi
    def write(self, values):
        if not self.user_has_groups(
                'library.group_library_manager'):
            if 'manager_remarks' in values:
                del values['manager_remarks']
        return super(LibraryLoanWizard, self).write(values)