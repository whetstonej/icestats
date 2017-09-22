# Icestats

Generates an interactive plot of listener connections from Icecast log data

### Requirements
- Python 2.7
- Flask
- Sqlite3

### Setup
1. Generate a blank database `sqlite3 data.db < icestats.sql`
2. Complete the configuration information required in `config.sample`
3. Run the data generation tool specifying the configuration file `python2 icegen.py config.sample`
4. Run the flask application and view in your web browser at 127.0.0.1:5000 `python2 icestats.py config.sample`
