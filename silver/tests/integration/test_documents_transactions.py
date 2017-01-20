# Copyright (c) 2017 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.core.exceptions import ValidationError
from mock import MagicMock, patch, call, PropertyMock

from django.test import TestCase

from silver.models import PaymentMethod
from silver.models import Transaction
from silver.models.payment_processors.base import PaymentProcessorBase
from silver.models.payment_processors.mixins import TriggeredProcessorMixin
from silver.tests.factories import TransactionFactory, ProformaFactory, \
    PaymentMethodFactory, InvoiceFactory
from silver.tests.utils import register_processor


class TriggeredProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    reference = 'triggeredprocessor'

    def execute_transaction(self, transaction):
        pass


class TestDocumentsTransactions(TestCase):
    def test_pay_documents_on_transaction_settle(self):
        transaction = TransactionFactory.create(
            state=Transaction.States.Pending,
        )
        transaction.settle()
        transaction.save()

        proforma = transaction.proforma
        invoice = transaction.invoice

        self.assertEqual(proforma.state, proforma.STATES.PAID)
        self.assertEqual(invoice.state, invoice.STATES.PAID)

    # also refunding needs to be tested when implemented

    @register_processor(TriggeredProcessor, display_name='TriggeredProcessor')
    def test_transaction_creation_for_issued_documents(self):
        """
            The happy case.
        """
        invoice = InvoiceFactory.create()
        customer = invoice.customer

        PaymentMethodFactory.create(
            payment_processor='triggeredprocessor', customer=customer,
            enabled=True,
            verified=True,
        )

        invoice.issue()

        transactions = Transaction.objects.filter(
            invoice=invoice, proforma=invoice.proforma
        )
        self.assertEqual(len(transactions), 1)


    @register_processor(TriggeredProcessor, display_name='TriggeredProcessor')
    def test_no_transaction_creation_for_issued_documents_case_1(self):
        """
            The payment method is not recurring
        """
        invoice = InvoiceFactory.create()
        customer = invoice.customer

        PaymentMethodFactory.create(
            payment_processor='triggeredprocessor', customer=customer,
            enabled=True,
            verified=False
        )

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor, execute_transaction=mock_execute):
            invoice.issue()

            transactions = Transaction.objects.filter(
                invoice=invoice, proforma=invoice.proforma
            )
            self.assertEqual(len(transactions), 0)

    @register_processor(TriggeredProcessor, display_name='TriggeredProcessor')
    def test_no_transaction_creation_for_issued_documents_case2(self):
        """
            The payment method is not usable
        """
        invoice = InvoiceFactory.create()
        customer = invoice.customer

        PaymentMethodFactory.create(
            payment_processor='triggeredprocessor', customer=customer,
            enabled=False
        )

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor, execute_transaction=mock_execute):
            invoice.issue()

            transactions = Transaction.objects.filter(
                invoice=invoice, proforma=invoice.proforma
            )
            self.assertEqual(len(transactions), 0)

    @register_processor(TriggeredProcessor, display_name='TriggeredProcessor')
    def test_no_transaction_creation_for_issued_documents_case3(self):
        """
            There already is an active (initial/pending) transaction for the
            document.
        """
        invoice = InvoiceFactory.create(state='issued')
        customer = invoice.customer

        payment_method = PaymentMethodFactory.create(
            payment_processor='triggeredprocessor', customer=customer,
            enabled=True,
            verified=True,
        )

        transaction = TransactionFactory.create(invoice=invoice,
                                                payment_method=payment_method)

        mock_execute = MagicMock()
        with patch.multiple(TriggeredProcessor, execute_transaction=mock_execute):
            self.assertRaises(ValidationError, TransactionFactory.create,
                              **{'invoice': invoice,
                                 'payment_method': payment_method})

            transactions = Transaction.objects.filter(
                payment_method=payment_method, invoice=invoice,
            )
            self.assertEqual(len(transactions), 1)
            self.assertEqual(transactions[0], transaction)

            self.assertEqual(mock_execute.call_count, 0)
