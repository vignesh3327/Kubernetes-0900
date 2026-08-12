# Kubernetes Service Account with AWS EKS Pod Identity

 - How to use a Kubernetes Service Account with AWS EKS Pod Identity to provide secure AWS permissions to pods without storing AWS credentials inside containers.

---

# Architecture Overview

![EKS Pod Identity](https://miro.medium.com/v2/resize:fit:1400/1*UQn0V6v7J4H9DqZfM9b6xA.png)

---

# What is a Kubernetes Service Account?

A Service Account in Kubernetes provides an identity for pods running inside the cluster.

Instead of using node-level IAM permissions, you can assign AWS permissions directly to specific pods using:

- Kubernetes Service Account
- AWS IAM Role
- EKS Pod Identity

This follows the least privilege principle and improves security.

---

# Prerequisites

Before starting, ensure you have:

- An AWS EKS Cluster
- AWS CLI configured
- kubectl installed
- IAM Role with required permissions
- EKS Pod Identity Agent installed

---

# Verify Pod Identity Agent

Check whether the EKS Pod Identity Agent is running inside the cluster.

```bash
kubectl get pods -n kube-system | grep pod-identity
```

Expected output:

```bash
eks-pod-identity-agent-xxxxx   Running
```

---

# Step 1 — Create Kubernetes Service Account

Create a service account named `s3-reader`.

## service-account.yaml

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader
  namespace: default
```

Apply the manifest:

```bash
kubectl apply -f service-account.yaml
```

Verify:

```bash
kubectl get serviceaccounts
```

---

# Step 2 — Create Pod Identity Association

Associate the Kubernetes service account with an AWS IAM Role.

```bash
aws eks create-pod-identity-association \
  --cluster-name naresh \
  --namespace default \
  --service-account s3-reader \
  --role-arn arn:aws:iam::590184008189:role/podid \
  --region us-east-1
```

---

# How It Works

1. Pod uses Kubernetes Service Account
2. Service Account is linked to IAM Role
3. EKS Pod Identity Agent injects temporary credentials
4. Pod accesses AWS services securely
5. No hardcoded AWS keys required

---

# Step 3 — Deploy Test Pod

Create a pod using the service account.

## pod.yaml

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: s3-test
spec:
  serviceAccountName: s3-reader

  containers:
    - name: aws-cli
      image: amazon/aws-cli
      command: ["sleep", "3600"]
```

Apply the pod:

```bash
kubectl apply -f pod.yaml
```

Verify pod status:

```bash
kubectl get pods
```

---

# Step 4 — Verify Service Account Used by Pod

Check which service account the pod is using.

```bash
kubectl get pod s3-test -o jsonpath='{.spec.serviceAccountName}'
```

Expected output:

```bash
s3-reader
```

---

# Step 5 — Verify Pod Identity Associations

List all Pod Identity Associations.

```bash
aws eks list-pod-identity-associations \
  --cluster-name naresh \
  --region us-east-1
```

---

# Step 6 — Test AWS Access from Pod

Connect to the pod:

```bash
kubectl exec -it s3-test -- sh
```

Check AWS identity:

```bash
aws sts get-caller-identity
```

Test S3 access:

```bash
aws s3 ls
```

If permissions are configured correctly, the pod can access S3 successfully.

---

# Security Benefits

Using EKS Pod Identity provides several advantages:

- No hardcoded AWS credentials
- Fine-grained IAM access control
- Pod-level permissions
- Improved security posture
- Temporary AWS credentials
- Easier IAM management

---

# Common Use Cases

- Accessing Amazon S3 from applications
- DynamoDB access from pods
- Accessing AWS Secrets Manager
- CloudWatch logging
- ECR image operations
- Multi-tenant Kubernetes environments

---

# Troubleshooting

## Pod Identity Agent Not Running

```bash
kubectl get pods -n kube-system
```

Ensure Pod Identity Agent is running.

---

## Verify IAM Role Permissions

Check attached IAM policies:

```bash
aws iam list-attached-role-policies --role-name podid
```

---

## Verify Association

```bash
aws eks list-pod-identity-associations \
  --cluster-name naresh \
  --region us-east-1
```

---

## Check Pod Logs

```bash
kubectl logs s3-test
```

---

# Project Structure

```text
.
├── service-account.yaml
├── pod.yaml
└── README.md
```

---

