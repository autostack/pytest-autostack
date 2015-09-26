from setuptools import setup

setup(
    name="pytest-autostack",
    use_scm_version={'write_to': 'autostack/_version.py'},
    description='py.test autostack plugin',
    long_description=open('README.md').read(),
    license='MIT',
    author='Avi Tal',
    author_email='avi3tal@gmail.com',
    url='https://github.com/autostack/pytest-autostack',
    platforms=['linux'],
    packages=['autostack'],
    entry_points={
        'pytest11': [
            'autostack = autostack.plugin',
            'autostack.sensor = autostack.sensor',
        ],
    },
    zip_safe=False,
    install_requires=['ansible', 'pytest>=2.4.2', 'py>=1.4.22', 'redis', 'six'],
    setup_requires=['setuptools_scm'],
    classifiers=[
        'Private :: Do Not Upload',
    ],
)
