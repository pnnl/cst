# Time-Series Data Logging
There will be things written here that will likely be very important.

## Overview of Postgres database

## Postgres Schema
Third form normal

One table per data type

Columns:
- federate
- sim time (ordinal time)
- time stamp
- Value
  - publication: 

## Time-Series APIs
Brief description of select APIs for writing and reading to and from the time-series database

Simple query APIs that put data into a Pandas dataframe (under the assumption that more people know how to manipulate Pandas DF than make Postgres queries)

Postgres query object is provided for those that prefer to write their own queries and access the data that way.

## Logger Federate
Built on federate.py

## Federate class logging
Purpose - faster as it saves a network hop


