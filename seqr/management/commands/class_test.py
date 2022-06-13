from django.core.management.base import BaseCommand

class Base(object):
    def __init__(self, a, b):
        self.a = a
        self.t = self.load_table(b)

    def load_table(self, x):
        print(f'in Base: {x}')
        return [x, self.a]

class A(Base):

    def load_table(self, x):
        print(f'in A: {x}')
        val = super(A, self).load_table(x)
        return val + val

class BMixin(object):

    def load_table(self, x):
        print(f'in B: {x}')
        val = super(BMixin, self).load_table(x + 1)
        return [self.a] + val

class B(BMixin, Base):
    pass
    # def load_table(self, x):
    #     return super(B, self).load_table(x + 1)

class All(BMixin, A):

    def load_table(self, x):
        b = super(All, self).load_table(x)
        print(f'sub B: {b}')
        a = A.load_table(self, x)
        print(f'sub A: {a}')
        return a + b

class Command(BaseCommand):


    def handle(self, *args, **options):
        print(f'Base: {Base(1, 2).t}')
        print('---')
        print(f'A: {A(1, 2).t}')
        print('---')
        print(f'B: {B(1, 2).t}')
        print('---')
        print(f'All: {All(1, 2).t}')

