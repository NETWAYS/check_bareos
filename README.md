# check_bareos

Icinga Monitoring Plugin to check Bareos Backup Director databases

The plugin connects to the Bareos database in order to retrieve data.

## Installation

The plugin requires at least Python 3.

Python dependencies:

* `psycopg2-binary`

## Usage

```
p check_bareos.py --help
usage: check_bareos.py [-h] -U USER [-p PASSWORD] [-H HOST] [-P PORT] [-d DATABASE] [-v]
                       {job,tape,status} ...

Check Plugin for Bareos Backup Status

positional arguments:
  {job,tape,status}
    job                 Specific checks on a job
    tape                Specific checks on a tapes
    status              Specific status informations

options:
  -h, --help            show this help message and exit

  -U USER, --user USER  user name for the database connections
  -p PASSWORD, --password PASSWORD
                        password for the database connections
  -H HOST, --Host HOST  database host
  -P PORT, --port PORT  database port
  -d DATABASE, --database DATABASE
                        database name
  -v, --version         show program's version number and exit
```

## Job

Check the status of Bareos Jobs.

```
usage: check_bareos.py job [-h] (-js | -j | -rt) [-n NAME] [-t TIME] [-u {GB,TB,PB}] [-w WARNING]
                           [-c CRITICAL] [-st {A,B,C,D,E,F,I,L,M,R,S,T,W,a,c,d,e,f,i,j,l,m,p,q,s,t}]
                           [-f] [-i] [-d]

options:
  -h, --help            show this help message and exit
  -js, --checkJobs      Check how many jobs are in a specific state [default=queued]
  -j, --checkJob        Check the state of a specific job [default=queued]
  -rt, --runTimeJobs    Check if a backup runs longer then n day
  -n NAME, --name NAME  Name of the job
  -t TIME, --time TIME  Time in days (default=7 days)
  -u {GB,TB,PB}, --unit {GB,TB,PB}
                        display unit
  -w WARNING, --warning WARNING
                        Warning value
  -c CRITICAL, --critical CRITICAL
                        Critical value
  -st {A,B,C,D,E,F,I,L,M,R,S,T,W,a,c,d,e,f,i,j,l,m,p,q,s,t}, --state {A,B,C,D,E,F,I,L,M,R,S,T,W,a,c,d,e,f,i,j,l,m,p,q,s,t}
                        Bareos Job State [default=C]
  -f, --full            Backup kind full
  -i, --inc             Backup kind inc
  -d, --diff            Backup kind diff
```

### Examples

Check if a job is runing longar than 7 days (default value):

```bash
check_bareos.py  -u bareos -d p job -rt -t 4 -st R  -w 1 -c 4
```

Check how much jobs are in the wating status:

```bash
check_bareos.py -u bareos -d p job  -js -w 50 -c 100
```

## Tape

Check the status of Bareos Tapes.

```
usage: check_bareos.py tape [-h] (-e | -ts | -ex | -wex | -r) [-w WARNING] [-c CRITICAL] [-m MOUNTS]
                            [-t TIME]

options:
  -h, --help            show this help message and exit
  -e, --emptyTapes      Count empty tapes in the storage (Status Purged/Expired)
  -ts, --tapesInStorage
                        Count how much tapes are in the storage
  -ex, --expiredTapes   Count how much tapes are expired
  -wex, --willExpire    Count how much tapes are will expire in n day
  -r, --replaceTapes    Count how much tapes should by replaced
  -w WARNING, --warning WARNING
                        Warning value
  -c CRITICAL, --critical CRITICAL
                        Critical value
  -m MOUNTS, --mounts MOUNTS
                        Amout of allowed mounts for a tape [used for replace tapes]
  -t TIME, --time TIME  Time in days (default=7 days)
```

### Examples

Check how much tapes are empty in the storage:

```bash
check_bareos.py -u bareos -d p tape -e -w 15 -c 10
```

Check how much tapes are expired:

```
check_bareos.py -u bareos -d p tape -ex
```

Check how much tapes will expire in the next 14 days;

```bash
check_bareos.py -u bareos -d p tape -wex -t 14 -w 10 -c 5
```

## Status

Check the status of various Bareos metrics.

```
usage: check_bareos.py status [-h] (-b | -e | -o | -fb) [-f] [-i] [-d] [-t TIME] [-w WARNING]
                              [-c CRITICAL] [-s SIZE] [-u {MB,GB,TB,PB,EB}]

options:
  -h, --help            show this help message and exit
  -b, --totalBackupsSize
                        the size of all backups in the database [use time and kind for mor
                        restrictions]
  -e, --emptyBackups    Check if a successful backup have 0 bytes [only wise for full backups]
  -o, --oversizedBackup
                        Check if a backup have more than n TB
  -fb, --failedBackups  Check if a backup failed in the last n day
  -f, --full            Backup kind full
  -i, --inc             Backup kind inc
  -d, --diff            Backup kind diff
  -t TIME, --time TIME  Time in days
  -w WARNING, --warning WARNING
                        Warning value [default=5]
  -c CRITICAL, --critical CRITICAL
                        Critical value [default=10]
  -s SIZE, --size SIZE  Border value for oversized backups [default=2]
  -u {MB,GB,TB,PB,EB}, --unit {MB,GB,TB,PB,EB}
                        display unit [default=TB]
```

### Examples


Check total size of all backups:

```bash
check_bareos.py -u bareos -d p status -b -w 400 -c 500
```

Check total size of all full backups:

```bash
check_bareos.py -u bareos -d p status -b -f -w 400 -c 500
```

Check total size of all diff backups:

```bash
check_bareos.py -u bareos -d p status -b -d -w 400 -c 500
```

Check total size of all inc backups:

```bash
check_bareos.py -u bareos -d p status -b -i -w 400 -c 500
```

Check if a full backup has 0 Bytes(is Empty) and trigger warning it is at least 1 and trigger ciritcal if more than 5 are empty:

```bash
check_bareos.py -u bareos -d p status -e -f -w 1 -c 5
```

Check if a diff/inc backup is larger than 2 TB (default value) and trigger warning it is at least 1 and trigger ciritcal if more than 5 are empty:

```bash
check_bareos.py -u bareos -d p status -o -d -i -w 1 -c 5
```
