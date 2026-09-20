# Kubernetes Production Incident: Application Ready but `/customers` Returned 500

## Incident Summary

The `bank-app` Kubernetes application Pods were running and passing readiness checks, but requests to the `/customers` endpoint returned HTTP 500.

The investigation required tracing the request from the Service through the Pod, application configuration, MySQL connectivity, and finally the database schema.

The incident was resolved by:

1. Configuring the application with the correct MySQL connection environment variables.
2. Correcting MySQL Secret key references in the MySQL Deployment.
3. Loading the required database schema and sample data.
4. Verifying the application endpoint successfully returned customer data.

---

## Environment

* Kubernetes: Minikube
* Namespace: `dev`
* Application: Flask
* Database: MySQL 8.4
* Application container port: `5000`
* Kubernetes Service: `bank-app`
* Database Service: `mysql`

---

## Initial Symptom

Pods appeared healthy:

```bash
kubectl get pods -n dev
```

The application Pod was:

```text
READY   STATUS
1/1     Running
```

The Service and endpoints were also present.

However:

```bash
curl http://bank-app/customers
```

returned:

```text
HTTP 500
```

The application logs showed:

```text
mysql.connector.errors.DatabaseError:
2003 (HY000): Can't connect to MySQL server on 'localhost:3306'
```

---

## Investigation

### 1. Verify Pod Status

```bash
kubectl get pods -n dev -o wide
```

The application Pods were running.

This ruled out:

* Pod scheduling failure
* ImagePullBackOff
* CrashLoopBackOff
* Container startup failure

---

### 2. Verify Service

```bash
kubectl get svc -n dev
```

The `bank-app` Service existed and exposed port `80`.

---

### 3. Verify Service Endpoints

```bash
kubectl get endpoints bank-app -n dev
```

Endpoints were present:

```text
10.244.x.x:5000
10.244.x.x:5000
10.244.x.x:5000
```

This confirmed that the Service selector was finding the application Pods.

---

### 4. Verify Readiness

The application Deployment contained an HTTP readiness probe:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 5000
  periodSeconds: 5
  failureThreshold: 2
```

The `/health` endpoint returned HTTP 200:

```text
{
  "application": "Srinivas Bank",
  "database": "Connected",
  "status": "UP"
}
```

The Pod was therefore considered Ready and remained in the Service endpoints.

A temporary readiness failure was also observed during Pod startup:

```text
Readiness probe failed:
connect: connection refused
```

This was expected while the application was starting and did not cause the persistent HTTP 500.

---

## Root Cause 1: Missing Database Configuration

The Flask application reads database configuration from environment variables:

```python
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "bankuser"),
    "password": os.getenv("DB_PASSWORD", "bank123"),
    "database": os.getenv("DB_NAME", "bankdb")
}
```

The running application Pod initially had no `DB_*` environment variables.

Therefore the application used the default:

```text
DB_HOST=localhost
```

Inside a Kubernetes Pod, `localhost` means the **same Pod**, not the MySQL Pod.

MySQL was running in a separate Pod.

### Verification

```bash
kubectl exec -n dev deploy/bank-app -- env | grep '^DB_'
```

Initially there was no output.

The application consequently attempted:

```text
localhost:3306
```

instead of:

```text
mysql:3306
```

---

## Fix 1: Configure Database Connection

The application Deployment was updated with:

```yaml
env:
  - name: DB_HOST
    value: mysql

  - name: DB_PORT
    value: "3306"

  - name: DB_NAME
    value: bankdb

  - name: DB_USER
    value: bankuser

  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: mysql-secret
        key: MYSQL_PASSWORD
```

The password is obtained from the Kubernetes Secret instead of being stored directly in the Deployment.

After applying the Deployment:

```bash
kubectl exec -n dev deploy/bank-app -- env | grep '^DB_'
```

returned the expected configuration.

---

## Root Cause 2: Database Schema Was Missing

After fixing the connection configuration, the application could reach MySQL.

The error changed to:

```text
mysql.connector.errors.ProgrammingError:
1146 (42S02): Table 'bankdb.customer' doesn't exist
```

This was an important troubleshooting step.

It proved that:

* Kubernetes DNS was working.
* The `mysql` Service was reachable.
* MySQL was accepting connections.
* Database credentials were valid.
* The `bankdb` database existed.
* The required `customer` table did not exist.

---

## Fix 2: Load Database Schema

The existing schema was loaded into MySQL:

```bash
kubectl exec -i -n dev <mysql-pod> -- \
  mysql -ubankuser -p bankdb < database/schema.sql
```

Sample data was then loaded:

```bash
kubectl exec -i -n dev <mysql-pod> -- \
  mysql -ubankuser -p bankdb < database/sample-data.sql
```

The actual database password was supplied interactively and was not committed to Git.

---

## Supporting Configuration Fix: MySQL Secret Keys

The MySQL Deployment was also corrected to reference the actual keys present in the Kubernetes Secret.

Updated references:

```yaml
- name: MYSQL_ROOT_PASSWORD
  valueFrom:
    secretKeyRef:
      name: mysql-secret
      key: MYSQL_ROOT_PASSWORD
```

and:

```yaml
- name: MYSQL_PASSWORD
  valueFrom:
    secretKeyRef:
      name: mysql-secret
      key: MYSQL_PASSWORD
```

The previous Deployment referenced different key names.

---

## Final Verification

The application was tested from inside the Kubernetes cluster:

```bash
kubectl run curl-test -n dev --rm -it \
  --image=curlimages/curl \
  --restart=Never -- \
  curl -s http://bank-app/customers
```

The request successfully returned the customer HTML page and customer records.

This confirmed:

```text
Client
  ↓
Kubernetes Service
  ↓
Ready bank-app Pod
  ↓
Flask Application
  ↓
mysql Service
  ↓
MySQL Pod
  ↓
bankdb
  ↓
customer table
  ↓
Successful response
```

---

## Troubleshooting Method Used

The incident was investigated from the outside inward:

```text
1. Client request
       ↓
2. Service
       ↓
3. Endpoints / EndpointSlice
       ↓
4. Pod readiness
       ↓
5. Application endpoint
       ↓
6. Application logs / traceback
       ↓
7. Environment configuration
       ↓
8. Kubernetes DNS / Service
       ↓
9. MySQL connectivity
       ↓
10. Database schema
```

This prevented assuming that a `Running` Pod automatically meant the application was working.

---

## Important Lessons

### `Running` does not mean application is healthy

A Pod can be:

```text
Running
```

while the application is returning HTTP 500.

Readiness determines whether Kubernetes should send Service traffic to the Pod.

---

### `localhost` inside a Pod means the Pod itself

This is incorrect when MySQL runs in another Pod:

```text
DB_HOST=localhost
```

The Kubernetes Service name should be used:

```text
DB_HOST=mysql
```

Kubernetes DNS resolves `mysql` to the MySQL Service.

---

### Readiness and Liveness are different

Readiness:

```text
Should this Pod receive traffic?
```

Liveness:

```text
Should Kubernetes restart this container?
```

A failed readiness probe removes the Pod from Service traffic but does not restart the container.

---

### Service endpoints do not prove the application is working

Endpoints only prove that Kubernetes selected Ready Pods and knows where to send traffic.

The application can still return HTTP 500 after receiving the request.

---

### Error progression is valuable evidence

The incident produced different errors as each layer was fixed:

```text
localhost:3306 connection refused
        ↓
Database connection fixed
        ↓
customer table does not exist
        ↓
Schema loaded
        ↓
Successful customer response
```

Each error narrowed the remaining problem.

---

## Production Considerations

For a production deployment, database initialization should not depend on manually executing SQL commands against a running Pod.

A production implementation should use an appropriate database migration or initialization process.

Secrets should also be managed through a proper secret-management solution rather than storing credentials directly in manifests.

The current setup is a Kubernetes learning environment designed to reproduce and troubleshoot production-style failures.

---

## Incident Status

**Resolved**

Application connectivity, Kubernetes Service routing, readiness, MySQL connectivity, database schema, and application endpoint functionality were verified successfully.

## Key Interview Explanation

> The Pods were Running and Ready, and the Service had valid endpoints, but `/customers` returned HTTP 500. I traced the request into the application logs and found that the application was connecting to `localhost:3306` because the DB environment variables were missing. I configured the application to use the `mysql` Kubernetes Service and sourced the password from a Secret. The next error showed that the `customer` table was missing, so I loaded the database schema and sample data. Finally, I tested the endpoint from inside the cluster and confirmed that it returned the expected customer data.

