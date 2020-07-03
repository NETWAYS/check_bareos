# check_bareos
Icinga Monitoring Plugin to check Bareos Backup Director databases. Usable in sensu/sensu-go

Main Git Repository: <https://github.com/VeselaHouba/check_bareos>

At the moment this is a fork repository to make it to a synchronised project with this site.

This project is mainly aimed at fixing some bugs.

If you want to add features contribute in the git project or sent an email to the author or git repository owner.


## Check Examples

Note: use the postgresql database bareos and login without password


**Check if a full backup has 0 Bytes(is Empty) and trigger warning it is at least 1 and trigger ciritcal if more than 5 are empty**
```BASH
check_bareos.py -u bareos -d p status -e -f -w 1 -c 5
```

**Check if a diff/inc backup is larger than 2 TB (default value) and trigger warning it is at least 1 and trigger ciritcal if more than 5 are empty**
```BASH
check_bareos.py -u bareos -d p status -o -d -i -w 1 -c 5
```

**Check how much tapes are empty in the storage**
```BASH
check_bareos.py -u bareos -d p tape -e -w 15 -c 10
```

**Check total size of all backups**
```BASH
check_bareos.py -u bareos -d p status -b -w 400 -c 500
```

**Check total size of all full backups**
```BASH
check_bareos.py -u bareos -d p status -b -f -w 400 -c 500
```

**Check total size of all diff backups**
```BASH
check_bareos.py -u bareos -d p status -b -d -w 400 -c 500
```

**Check total size of all inc backups**
```BASH
check_bareos.py -u bareos -d p status -b -i -w 400 -c 500
```

**Check if a job is runing longar than 7 days (default value)**
```BASH
check_bareos.py  -u bareos -d p job -rt -t 4 -st R  -w 1 -c 4
```

**Check how much jobs are in the wating status**
```BASH
check_bareos.py -u bareos -d p job  -js -w 50 -c 100
```

**Check how much tapes are expired**
```BASH
check_bareos.py -u bareos -d p tape -ex
```

**Check how much tapes will expire in the next 14 days**
```BASH
check_bareos.py -u bareos -d p tape -wex -t 14 -w 10 -c 5
```
