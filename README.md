# VMAX FAST VP Report

This tool produces a report showing VP and FAST VP information for every device in a specified VMAX array. The information provided includes the bound pool, capacity information (provisioned and allocated), written capacity distribution over pools, associated Storage Groups, the FAST-associated Storage Group (if any), the FAST Policy name, and the FAST Policy tier percentages.

Among other use cases, this can be useful for ensuring that a particular array conforms to [basic FAST VP Best practices](http://blog.scummins.com/?p=87).

Please note that this script is designed for VMAX1 and VMAX2. This includes the original VMAX, VMAX SE, VMAXe, VMAX 10K, VMAX 20K, and VMAX 40K. It will not work with the new VMAX3.

I find it useful to pipe the output to a csv file (using the -csv) option, and then import into a spreadsheet for filtering/analysis. For example: filter by bound pool to find devices that are bound to the wrong pool. Or filter by FAST Policy to find devices that are not associated to a policy.


# Usage

~~~
usage: fastvp_report.py [-h] -sid SID [-showallsgs] [-csv] [-quotedcsv]

Reports FASTVP information per Symmetrix Device.

optional arguments:
  -h, --help   show this help message and exit

Required arguments:
  -sid SID     Symmetrix serial number

Additional optional arguments:
  -showallsgs  Flag; Shows all Storage Groups (not just FASTVP SGs)
  -csv         Flag; Outputs in CSV format
  -quotedcsv   Flag; Outputs in quoted CSV format
~~~


# Example Output

```
TDEV    TotalGB   WrittenGB   BoundPool   FastSG                           FastPolicy   Policy%       EFDR531   FC15KR531   SATAR662
02080   1024.0    540.4       FC15KR531   esx_prod_01                   Production   100/100/100   52.7      166.3       330.0
02088   2048.0    1860.4      FC15KR531   esx_backup01                  Production   100/100/100   55.1      703.7       1102.1
02098   1024.0    752.3       FC15KR531   esx_prod_01                   Production   100/100/100   29.1      165.0       599.1
020A0   1024.0    686.1       FC15KR531   esx_prod_01                   Production   100/100/100   97.0      228.2       373.0
020A8   1024.0    658.2       FC15KR531   esx_prod_01                   Production   100/100/100   57.5      185.7       417.4
020B0   1024.0    608.9       FC15KR531   esx_prod_01                   Production   100/100/100   42.6      161.5       458.6
020B8   1024.0    683.4       FC15KR531   esx_prod_01                   Production   100/100/100   28.7      261.0       395.2
020C0   1024.0    783.3       FC15KR531   esx_prod_01                   Production   100/100/100   60.2      199.1       525.8
020C8   1024.0    756.2       FC15KR531   esx_prod_01                   Production   100/100/100   51.8      271.4       435.7
020D0   1024.0    674.6       FC15KR531   esx_prod_01                   Production   100/100/100   190.4     103.7       381.7
020D8   2048.0    1824.1      FC15KR531   esx_prod_01                   Production   100/100/100   151.2     1102.1      572.5
020E8   1024.0    737.8       FC15KR531   esx_prod_02                   Production   100/100/100   45.1      184.8       510.0
020F0   1024.0    741.3       FC15KR531   esx_prod_02                   Production   100/100/100   34.8      211.2       497.5
020F8   1024.0    747.4       FC15KR531   esx_prod_02                   Production   100/100/100   27.5      228.0       497.4
02100   1024.0    796.5       FC15KR531   esx_prod_02                   Production   100/100/100   122.8     148.9       526.8
02108   1024.0    829.1       FC15KR531   esx_prod_02                   Production   100/100/100   144.0     187.8       498.4
02110   1024.0    821.7       FC15KR531   esx_prod_02                   Production   100/100/100   110.6     162.7       550.3
02118   1024.0    672.5       FC15KR531   esx_prod_02                   Production   100/100/100   32.8      189.8       456.1
02120   1024.0    854.0       FC15KR531   esx_prod_02                   Production   100/100/100   79.9      427.4       348.2
02128   2048.0    1701.7      FC15KR531   esx_prod_02                   Production   100/100/100   61.4      392.3       1251.1
02138   1024.0    452.5       FC15KR531   esx_sql                       Production   100/100/100   5.4       38.2        412.3
02140   1024.0    798.1       FC15KR531   esx_sql                       Production   100/100/100   88.3      493.9       218.1
02148   1024.0    295.0       FC15KR531   esx_sql                       Production   100/100/100   0.6       3.8         292.7
02150   1024.0    424.7       FC15KR531   esx_sql                       Production   100/100/100   11.9      85.2        334.6
02158   1024.0    321.1       FC15KR531   esx_sql                       Production   100/100/100   0.0       0.1         322.4
02160   1024.0    824.5       FC15KR531   esx_sql                       Production   100/100/100   30.5      524.1       272.6
02168   1024.0    555.1       FC15KR531   esx_sql                       Production   100/100/100   19.4      279.5       408.7
02170   1024.0    901.4       FC15KR531   esx_sql                       Production   100/100/100   29.2      405.5       561.1
02178   1024.0    1014.0      FC15KR531   esx_sql                       Production   100/100/100   17.0      890.5       113.1
```
