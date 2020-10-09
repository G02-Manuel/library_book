from odoo import models, fields, api, exceptions
from odoo.fields import Date as fDate
from datetime import timedelta
#first module

class LibraryBook(models.Model):
    _name = 'library.book'
    #_inherit = ['base.archive']
    short_name = fields.Char('Short Title')
    notes = fields.Text('Internal Notes')
    state = fields.Selection(
        [('draft', 'Not Available'),
         ('available', 'Available'),
         ('lost', 'Lost')],
        'State')
    manager_remarks = fields.Text('Manager Remarks')
    description = fields.Html('Description')
    cover = fields.Binary('Book Cover')
    out_of_print = fields.Boolean('Out of print?')
    date_release = fields.Date('Release Date')
    date_updated = fields.Datetime('Last Updated')
    pages = fields.Integer('Number of Pages')
    reader_rating = fields.Float(
        'Reader Average Rating',
        digits=(14, 4), #Optional precision(total, decimals)
    )
    _order = 'date_release desc, name'
    name = fields.Char('Title', required=True)
    author_ids = fields.Many2many(
        'res.partner',
        string='Authors'
    )
    date_start = fields.Date(
        related='library_member.date_start'
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency'
    )
    retail_price = fields.Monetary(
        'Retail Price',
        # optional: currency_field='currency_id'
    )
    publisher_id = fields.Many2one(
        'res.partner', string='Publisher',
    )
    publisher_city = fields.Char(
        'Publisher City',
        related='publisher_id.city',
        readonly=True
    )
    library_member = fields.Many2one(
        'library.member'
    )
    age_days = fields.Float(
        string='Days Since Release',
        compute='_compute_age',
        inverse='_inverse_age',
        search='_search_age',
        store=False,
        compute_sudo=False,
    )

    update_days = fields.Float(
        string='Days Since Update',
        compute='_compute_age_update',
        inverse='_inverse_age',
        search='_search_age',
        store=False,
        compute_sudo=False,
    )

    pages = fields.Integer(
        string='Number or Pages',
        default=0,
        help='Total book page count',
        groups='base.group_user',
        states={'lost': [('readonly', True)]},
        copy=True,
        index=False,
        readonly=False,
        required=False,
        company_dependent=False,
    )

    short_name = fields.Char(
        string='Short Title',
        size=100
    )

    description = fields.Html(
        string='Description',
        sanitize=True,
        strip_style=False,
        translate=False,
    )

    @api.depends('date_release')
    def _compute_age(self):
        today = fDate.from_string(fDate.today())
        for book in self.filtered('date_release'):
            delta = (today -
                     fDate.from_string(book.date_release))
            book.age_days = delta.days

    @api.depends('date_updated')
    def _compute_age_update(self):
        today = fDate.from_string(fDate.today())
        for book in self.filtered('date_updated'):
            delta = (today -
                     fDate.from_string(book.date_updated))
            book.update_days = delta.days

    @api.multi
    def name_get(self):
        result = []
        for book in self:
            authors = book.author_ids.mapped('name')
            name = '%s (%s)' % (book.name, ', '.join(authors))
            result.append((book.id, name))
            return result

    @api.model
    def _name_search(self, name='', args=None, operator='ilike',
                     limit=100, name_get_uid=None):
        args = [] if args is None else args.copy()
        if not(name == '' and operator == 'ilike'):
            args += ['!', '!',
                     ('name', operator, name),
                     ('isbn', operator, name),
                     ('author_ids.name', operator, name)
                    ]
        return super(LibraryBook, self)._name_search(
            name='', args=args, operator='ilike',
            limit=limit, name_get_uid=name_get_uid)

    def _inverse_age(self):
        today = fDate.from_string(fDate.context_today(self))
        for book in self.filtered('date_release'):
            d = today - timedelta(days=book.age_days)
            book.date_release = fDate.to_string(d)

    def _search_age(self, operator, value):
        today = fDate.from_string(fDate.context_today(self))

        value_days = timedelta(days=value)
        value_date = fDate.to_string(today - value_days)
        # convert the operator:
        # book with age > value have a date < value_date
        operator_map = {
            '>': '<', '>=': '<=',
            '<': '>', '<=': '>=',
        }
        new_op = operator_map.get(operator, operator)
        return [('date_release', new_op, value_date)]


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _name = 'library.member.rest'
    _rec_name = 'published_book_ids'
    _order = 'name'
    published_book_ids = fields.One2many(
        'library.book', 'publisher_id',
        string='Published Books'
    )
    authored_book_ids = fields.Many2many(
        'library.book', string='Author Books'
    )
    count_books = fields.Integer(
        'Number of Authored Books',
        compute='_compute_count_books'
    )

    @api.depends('authored_book_ids')
    def _compute_count_books(self):
        for r in self:
            r.count_books=len(r.authored_book_ids)


class BaseArchive(models.AbstractModel):
    _name = 'base.archive'
    active = fields.Boolean(default=True)

    def do_archive(self):
        for record in self:
            record.active = not record.active


class LibraryMember(models.Model):
    _name = 'library.member'
    _rec_name = 'partner_id'
    partner_id = fields.Many2one(
        'res.partner',
        ondelete='cascade'
    )
    date_start = fields.Date('Member Since')
    date_end = fields.Date('Termination Date')
    member_number = fields.Char()
    date_of_birth = fields.Date('Date of birth')
    loan_duration = fields.Integer('Loan duration',
                                   default=15,
                                   required=True)

    @api.model
    def is_allowed_transition(self, old_state, new_state):
        allowed = [('draft', 'available'),
                   ('available', 'borrowed'),
                   ('borrowed', 'available'),
                   ('available', 'lost'),
                   ('borrowed', 'lost'),
                   ('lost', 'available')]
        return (old_state, new_state) in allowed

    @api.multi
    def change_state(self, new_state):
        for book in self:
            if book.is_allowed_transition(book.state,
                                          new_state):
                book.state = new_state
            else:
                continue


class LibraryBookLoan(models.Model):
    _name = 'library.book.loan'
    expected_return_date = fields.Date('Due for', required=True)

    @api.multi
    def record_loans(self):
        for wizard in self:
            books = wizard.book_ids
            loan = self.env['library.book.loan']
            for book in wizard.book_ids:
                values = wizard._prepare_loan(book)
                loan.create(values)

    @api.multi
    def _prepare_loan(self, book):
        return {'member_id': self.member_id.id,
                'book_id': book.id}

    @api.multi
    def write(self, values):
        if not self.user_has_groups(
                'library.group_library_manager'):
            if 'manager_remarks' in values:
                raise exceptions.UserError(
                    'You are not allowed to modify'
                    'manager_remarks'
                )
            return super(LibraryBook, self).write(values)

    @api.model
    def fields_get(self,
                   allfields=None,
                   attributes=None):
        if not self.user_has_groups(
                'library.group_library_manager'):
            if 'manager_remarks' in fields:
                fields['manager_remarks']['readonly'] = True


class MyModel(models.Model):
    _name = 'my.model'

    @api.multi
    def write(self, values):
        super(MyModel, self).write(values)
        if self.env.context.get('MyModelLoopBreak'):
            return
        self = self.with_context(MyModelLoopBreak=True)
        self.compute_things()

