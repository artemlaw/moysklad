from setuptools import setup, find_packages

setup(
    name='moysklad',
    version='0.1.1',
    packages=find_packages(),
    install_requires=['requests', 'pymupdf', 'reportlab'],
    package_data={'moysklad': ['Roboto-Bold.ttf']},
    include_package_data=True,
    author='Lubentsov Artem',
    author_email='artem.law@mail.ru',
    description='Integration module MoySklad',
    url='https://github.com/artemlaw/moysklad',
)