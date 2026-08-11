# Kubernetes Requests vs Limits Explained

This project explains Kubernetes resource management using:

* Requests
* Limits
* CPU throttling
* Memory OOMKilled
* QoS Classes
* CrashLoopBackOff scenarios

Understanding requests and limits is very important for managing stable and reliable Kubernetes workloads.

---

# What are Requests and Limits?

Kubernetes allows defining resource requirements for containers.

## Example Resource Configuration

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "200m"

  limits:
    memory: "512Mi"
    cpu: "500m"
```

---

# Kubernetes Resource Architecture

```text
                    +----------------------+
                    |    Container Starts  |
                    +----------+-----------+
                               |
                               v
                +-----------------------------+
                | Kubernetes Scheduler Checks |
                |       Requests Values       |
                +--------------+--------------+
                               |
                               v
              +----------------------------------+
              | Node has enough CPU & Memory ?   |
              +---------------+------------------+
                              |
                   +----------+----------+
                   |                     |
                   | YES                 | NO
                   v                     v
          +----------------+      +------------------+
          | Pod Scheduled  |      | Pod Pending      |
          +--------+-------+      +------------------+
                   |
                   v
         +-----------------------+
         | Container Running     |
         +-----------+-----------+
                     |
                     v
         +-----------------------+
         | Resource Usage Grows  |
         +-----------+-----------+
                     |
         +-----------+-----------+
         |                       |
         v                       v
+------------------+   +-------------------+
| CPU exceeds limit|   | Memory exceeds    |
|                  |   | limit             |
+--------+---------+   +---------+---------+
         |                       |
         v                       v
+------------------+   +-------------------+
| CPU Throttling   |   | OOMKilled         |
| App becomes slow |   | Container Killed  |
+------------------+   +---------+---------+
                                 |
                                 v
                      +----------------------+
                      | Kubernetes Restarts  |
                      | Container            |
                      +----------+-----------+
                                 |
                                 v
                    +------------------------+
                    | Repeated Failures ?    |
                    +-----------+------------+
                                |
                      +---------+---------+
                      | YES               |
                      v                   |
             +-------------------+        |
             | CrashLoopBackOff  |<-------+
             +-------------------+
```

---

# 1. What is Requests?

Requests = minimum resources Kubernetes guarantees to the container.

## Example

```yaml
requests:
  memory: "256Mi"
  cpu: "200m"
```

Means Kubernetes schedules this Pod only on a node having:

* At least 256Mi memory available
* At least 0.2 CPU available

---

# Important Notes About Requests

* Requests are mainly used for scheduling
* Requests guarantee minimum resources
* Requests do NOT stop the application from using more resources
* Container can use more than requests if resources are available

---

# Request Scheduling Flow

```text
          +----------------------+
          | Pod Created          |
          +----------+-----------+
                     |
                     v
          +----------------------+
          | Scheduler Checks     |
          | Resource Requests    |
          +----------+-----------+
                     |
        +------------+------------+
        |                         |
        | Enough Resources        | No Resources
        v                         v
+------------------+     +------------------+
| Pod Scheduled    |     | Pod Pending      |
+------------------+     +------------------+
```

---

# 2. What is Limits?

Limits = maximum resources container can use.

## Example

```yaml
limits:
  memory: "512Mi"
  cpu: "500m"
```

Means:

* Memory cannot exceed 512Mi
* CPU cannot exceed 0.5 CPU core

---

# CPU vs Memory Behavior

This is the most important concept.

| Resource | If Limit Exceeded            |
| -------- | ---------------------------- |
| CPU      | Throttled (slowed down)      |
| Memory   | Container killed (OOMKilled) |

---

# 3. CPU Limit Behavior

## Example

```yaml
limits:
  cpu: "500m"
```

If application tries to use:

* 600m
* 700m
* 1 CPU

Then Kubernetes/Linux:

* Does NOT kill container
* Simply throttles CPU usage

---

# CPU Throttling Effects

Application becomes:

* Slow
* Delayed
* High response time

But container continues running.

---

# CPU Throttling Architecture

```text
        +----------------------+
        | CPU Limit = 500m     |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | App tries 700m CPU   |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Linux CFS Throttling |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Container Still Runs |
        | App Becomes Slow     |
        +----------------------+
```

---

# 4. Memory Limit Behavior (OOMKilled)

## Example

```yaml
limits:
  memory: "512Mi"
```

If application uses:

* 520Mi
* 700Mi
* 1Gi

Then:

* Linux Out Of Memory Killer (OOM Killer) kills the container
* Pod status becomes:

```text
OOMKilled
```

Kubernetes then restarts the container.

If repeated:

```text
CrashLoopBackOff
```

---

# OOMKilled Flow Architecture

```text
        +----------------------+
        | Memory Limit 512Mi   |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | App Uses 530Mi       |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | OOM Killer Triggered |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Container Killed     |
        | Status: OOMKilled    |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Kubernetes Restart   |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Continuous Failure ? |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | CrashLoopBackOff     |
        +----------------------+
```

---

# 5. When Exactly OOM Happens

OOM happens when:

```text
Container memory usage > memory limit
```

## Example Timeline

```text
memory limit = 512Mi

app starts        -> 200Mi
traffic increases -> 350Mi
cache grows       -> 480Mi
spike happens     -> 530Mi

=> OOMKilled
```

---

# 6. Important: Requests DO NOT Prevent OOM

## Example

```yaml
requests:
  memory: "256Mi"

limits:
  memory: "512Mi"
```

Application can still use:

* 300Mi
* 400Mi
* 500Mi

OOM occurs only after crossing:

```text
512Mi
```

NOT after crossing request.

---

# Requests vs Limits Architecture

```text
        +----------------------+
        | Request = 256Mi      |
        | Limit   = 512Mi      |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | App Uses 300Mi       |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Allowed              |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | App Uses 530Mi       |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | OOMKilled            |
        +----------------------+
```

---

# 7. If NO Memory Limit is Set

## Example

```yaml
resources:
  requests:
    memory: "256Mi"
```

No limit defined.

Then application may consume:

* 1Gi
* 2Gi
* Entire node memory

---

# Possible Problems Without Limits

* Node memory exhausted
* Other Pods killed
* Node instability
* Cluster performance issues

---

# No Memory Limit Architecture

```text
        +----------------------+
        | No Memory Limit      |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | App Memory Grows     |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Entire Node Memory   |
        | Consumed             |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Node Instability     |
        | Other Pods Killed    |
        +----------------------+
```

---

# 8. OOMScore and Who Gets Killed

Linux chooses processes to kill using:

* oom_score
* Kubernetes QoS class

---

# Kubernetes QoS Classes

| QoS Class  | Condition          |
| ---------- | ------------------ |
| Guaranteed | requests = limits  |
| Burstable  | requests < limits  |
| BestEffort | No requests/limits |

---

# Kill Priority During Node Memory Pressure

```text
BestEffort  -> killed first
Burstable   -> killed next
Guaranteed  -> killed last
```

---

# QoS Architecture

```text
                 +----------------------+
                 | Node Memory Pressure |
                 +----------+-----------+
                            |
                            v
               +-------------------------+
               | Linux Selects Victims   |
               +------------+------------+
                            |
        +-------------------+-------------------+
        |                   |                   |
        v                   v                   v
+---------------+   +---------------+   +---------------+
| BestEffort    |   | Burstable     |   | Guaranteed    |
| Killed First  |   | Killed Next   |   | Killed Last   |
+---------------+   +---------------+   +---------------+
```

---

# Example Full Resource Configuration

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo

spec:
  containers:
    - name: nginx
      image: nginx

      resources:
        requests:
          memory: "256Mi"
          cpu: "200m"

        limits:
          memory: "512Mi"
          cpu: "500m"
```

---

# Verify Resource Usage

## Check pod

```bash
kubectl get pods
```

## Describe pod

```bash
kubectl describe pod resource-demo
```

## Check resource usage

```bash
kubectl top pod
```

## Check events

```bash
kubectl get events
```

---

# Common Errors

## OOMKilled

```text
OOMKilled
```

Reason:

* Memory exceeded limit

---

## CrashLoopBackOff

```text
CrashLoopBackOff
```

Reason:

* Continuous container restarts

---

## Pending Pod

```text
0/3 nodes available: insufficient memory
```

Reason:

* Scheduler cannot find enough requested resources

---

# Best Practices

* Always define requests and limits
* Keep realistic memory limits
* Monitor application memory usage
* Avoid unlimited containers
* Use Guaranteed QoS for critical applications
* Monitor OOMKilled events regularly

---

# Interview Questions

## What is the difference between requests and limits?

| Requests                     | Limits                    |
| ---------------------------- | ------------------------- |
| Minimum guaranteed resources | Maximum allowed resources |
| Used for scheduling          | Used for enforcement      |

---

## What happens if CPU limit exceeds?

CPU is throttled. Container is NOT killed.

---

## What happens if memory limit exceeds?

Container gets killed with OOMKilled status.

---

## Does requests prevent OOMKilled?

No. OOM happens only after crossing memory limit.

---

## What is CrashLoopBackOff?

Continuous container restarts due to repeated failures.

---

## Which QoS class is safest?

Guaranteed QoS because it gets killed last during memory pressure.

---
