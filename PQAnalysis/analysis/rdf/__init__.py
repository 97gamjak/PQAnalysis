"""
A package containing classes and functions to handle radial distribution functions.

Classes
-------
:py:class:`~PQAnalysis.analysis.rdf.rdf.RDF`
    A class to handle radial distribution functions.
:py:class:`~PQAnalysis.analysis.rdf.rdfInputFileReader.RDFInputFileReader`
    A class to read RDFs from input files.
:py:class:`~PQAnalysis.analysis.rdf.rdfOutputFileWriter.RDFDataWriter`
    A class to write RDFs to output files.
:py:class:`~PQAnalysis.analysis.rdf.rdfOutputFileWriter.RDFLogWriter`
    A class to write log files.
"""

from .api import rdf
from .rdf import RDF
from .rdfInputFileReader import RDFInputFileReader
from .rdfOutputFileWriter import RDFDataWriter, RDFLogWriter
