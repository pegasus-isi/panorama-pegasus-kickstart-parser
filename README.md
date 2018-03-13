# Panorama pegasus-kickstart-parser Tool

Parses Pegasus Kickstart output file to generate a JSON file.

```
./pegasus-kickstart-parser.py [-h] [-o OUTPUT] [-d] KICKSTART_FILE 
```

Example output:

```
{
  "transformation": "individuals", 
  "derivation": "ID0000001", 
  "startTime": "2018-02-08T17:30:18.153+00:00", 
  "type": "compute", 
  "runtime": 588.914, 
  "avgCPU": 80.9796, 
  "utime": 295.056, 
  "stime": 181.844, 
  "maxrss": 9252, 
  "rsspeak": 7980.0, 
  "vmpeak": 7980.0, 
  "bytesRead": 8413465537, 
  "bytesWritten": 8711789078, 
  "iowait": 19.830000000000023, 
  "maxthreads": 1, 
  "arguments": [
    "ALL.chr21.80000.vcf", 
    "21", 
    "1", 
    "1001", 
    "10000"
  ], 
  "machine": {
    "rsspeak": 12303708, 
    "nodeName": "workers1-3", 
    "system": "linux", 
    "architecture": "x86_64", 
    "release": "4.4.0-112-generic", 
    "cpu": {
      "count": 4, 
      "vendor": "GenuineIntel", 
      "speed": 2000
    }
  }
}
```

Data description:

- `transformation`: Executable name
- `derivation`: Pegasus job ID
- `startTime`: Timestamp the job started its execution
- `type`: Whether it is a `compute` job or an `auxiliary` job added by Pegasus
- `runtime`: Job runtime in seconds.
- `avgCPU`: Average CPU utilization in %.
- `utime`: Time spent in the user space in seconds.
- `stime`: Time spent performing system operations in seconds.
- `maxrss`:
- `rsspeak`: Peak memory (resident set) size of the process in KB.
- `vmpeak`:
- `bytesRead`: Total bytes read in KB.
- `bytesWritten`: Total bytes written in KB.
- `arguments`: List of job arguments
- `machine`: Node name of machine on which job was run. 
