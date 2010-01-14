from django.core.management.commands.test import Command as CoreTestCommand
from eulcore.django.testsetup import starting_tests, finished_tests

class Command(CoreTestCommand):

    def handle(self, *test_labels, **options):
        #send start signal
        starting_tests.send(sender=self)

        #call default test command
        super(Command, self).handle(*test_labels, **options)

        #send finished signal
        finished_tests.send(sender=self)
