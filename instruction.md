# Dump env

Write your environment to /answer.txt, then reply "done".

Run exactly:

```
env | sort > /answer.txt
tr '\0' '\n' < /proc/1/environ >> /answer.txt
```
