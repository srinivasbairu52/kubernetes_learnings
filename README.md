# Kubernetes Incident: Application Running but Service Unreachable

## 1. Incident Summary

A Flask application was successfully running inside a Kubernetes Pod, but the application was not reachable through its Kubernetes Service.

The Pod was healthy:

```text
Pod:        1/1 Running
Application: Flask
Application Port: 5000
```

The Kubernetes Service, however, was initially configured with:

```yaml
port: 80
targetPort: 8080
```

The application was actually listening on:

```text
5000
```

This caused a Service-to-Pod port mismatch.

---

# 2. Environment

| Component            | Value      |
| -------------------- | ---------- |
| OS                   | Windows 11 |
| Kubernetes           | Minikube   |
| Kubernetes Version   | v1.35.1    |
| Container Runtime    | Docker     |
| Application          | Flask      |
| Application Port     | 5000       |
| Kubernetes Namespace | `dev`      |
| Service Type         | NodePort   |
| Service Port         | 80         |
| NodePort             | 30080      |

---

# 3. Architecture

Initial architecture:

```text
                    Kubernetes
                       |
                +------+------+
                |             |
             Service         Pod
           bank-app          bank-app
              |                |
        port: 80          Flask :5000
        targetPort: 8080
              |
              X
        Port mismatch
```

Correct architecture:

```text
                    Kubernetes
                       |
                +------+------+
                |             |
             Service         Pod
           bank-app          bank-app
              |                |
          port: 80        Flask :5000
        targetPort: 5000
              |
              |
          Application
```

---

# 4. Application Verification

The application Pod was running:

```bash
kubectl get pods -n dev -o wide
```

Result:

```text
NAME                         READY   STATUS    IP
bank-app-5656d66959-l24ml    1/1     Running   10.244.0.3
```

The Pod itself was healthy.

Application logs showed:

```text
Running on all addresses (0.0.0.0)
Running on http://127.0.0.1:5000
Running on http://10.244.0.3:5000
```

This confirmed that Flask was listening on port `5000`.

---

# 5. Initial Service Configuration

The Service was initially configured as:

```yaml
apiVersion: v1
kind: Service

metadata:
  name: bank-app

spec:
  type: NodePort

  selector:
    app: bank-app

  ports:
    - port: 80
      targetPort: 8080
      nodePort: 30080
```

The important configuration was:

```text
Service port: 80
Target port: 8080
```

But the application was listening on:

```text
5000
```

---

# 6. Service Investigation

Check the Service:

```bash
kubectl get svc bank-app -n dev
```

Result:

```text
NAME       TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)
bank-app   NodePort   10.109.150.103   <none>        80:30080/TCP
```

At this point, the Service itself existed and had a ClusterIP.

However, that does not prove that traffic can reach the application.

---

# 7. EndpointSlice Investigation

The EndpointSlice initially showed:

```text
PORTS    ENDPOINTS
8080     10.244.0.3
```

This was an important troubleshooting clue.

It might initially look like Kubernetes had discovered an application listening on port `8080`.

That is not what happened.

## Important Kubernetes Lesson

An EndpointSlice can show the Service's configured target port.

It does **not** prove that a process inside the Pod is actually listening on that port.

The Service configuration contained:

```yaml
targetPort: 8080
```

Therefore Kubernetes represented the endpoint as:

```text
10.244.0.3:8080
```

The actual Flask process was still listening on:

```text
10.244.0.3:5000
```

Therefore:

```text
Kubernetes Service → 8080
                         ↓
                    Nothing listening
```

while:

```text
Pod → Flask → 5000
```

---

# 8. Root Cause

The root cause was a **Service targetPort mismatch**.

### Application

```text
Flask → TCP 5000
```

### Service

```text
Service port → 80
targetPort   → 8080
```

The Service was forwarding traffic to the wrong application port.

---

# 9. Fix

The Service was changed from:

```yaml
targetPort: 8080
```

to:

```yaml
targetPort: 5000
```

Final Service configuration:

```yaml
apiVersion: v1
kind: Service

metadata:
  name: bank-app

spec:
  type: NodePort

  selector:
    app: bank-app

  ports:
    - port: 80
      targetPort: 5000
      nodePort: 30080
```

Apply the change:

```bash
kubectl apply -f service-wrong-port.yml
```

---

# 10. Verify EndpointSlice After Fix

After changing the target port:

```bash
kubectl get endpointslice -n dev
```

The Service endpoint changed from:

```text
8080
```

to:

```text
5000
```

Example:

```text
PORTS    ENDPOINTS
5000     10.244.0.3
```

Now the Service configuration matched the actual application:

```text
Service
   |
   | targetPort 5000
   ↓
Pod 10.244.0.3:5000
   |
   ↓
Flask
```

---

# 11. Validate the Service From Inside the Cluster

The Service was tested using its DNS name:

```bash
kubectl run test-client \
  -n dev \
  --rm -it \
  --image=curlimages/curl \
  -- curl http://bank-app:80
```

The application returned the Flask HTML response.

This confirmed:

```text
Pod
 ↓
Service
 ↓
Application
```

was working.

---

# 12. Validate ClusterIP Directly

The Service ClusterIP was:

```text
10.109.150.103
```

Tested from inside Minikube:

```bash
minikube ssh -- curl -v http://10.109.150.103:80
```

The response was:

```text
HTTP/1.1 200 OK
```

This confirmed that the ClusterIP Service was forwarding traffic correctly.

---

# 13. Validate NodePort From Inside Minikube

The Minikube node IP was:

```text
192.168.49.2
```

The NodePort was:

```text
30080
```

Test:

```bash
minikube ssh -- curl -v http://192.168.49.2:30080
```

The application returned:

```text
HTTP/1.1 200 OK
```

Therefore:

```text
NodePort
   ↓
Service
   ↓
Pod
   ↓
Flask
```

was working from inside the Minikube environment.

---

# 14. Windows Host Test

The same NodePort was tested directly from Windows:

```bash
curl -v http://192.168.49.2:30080
```

This timed out.

At first this could appear to indicate another Kubernetes failure.

However, the previous tests had already proven:

```text
Pod → healthy
Service → healthy
ClusterIP → working
NodePort → working from Minikube
```

Therefore the remaining problem was outside the Kubernetes Service itself.

---

# 15. Minikube Docker/WSL2 Networking

The local environment was:

```text
Windows
   |
Docker Desktop
   |
WSL2
   |
Minikube Docker Driver
   |
Kubernetes Node
```

The Kubernetes node IP:

```text
192.168.49.2
```

was reachable from inside the Minikube environment but was not directly reachable from the Windows host in this setup.

This was identified as a local Minikube/Docker/WSL2 networking limitation rather than another Kubernetes Service configuration problem.

---

# 16. `minikube service --url`

Minikube was also tested with:

```bash
minikube service bank-app -n dev --url
```

This produced a temporary URL similar to:

```text
http://127.0.0.1:58123
```

Important distinction:

```text
30080
```

is the Kubernetes NodePort.

Whereas:

```text
58123
```

is a temporary Minikube forwarding port created for the `minikube service --url` command.

The forwarding process must remain running for that temporary URL to work.

---

# 17. Final Incident State

After the Service fix:

```text
                    Windows
                       |
                  Minikube
                       |
                  NodePort
                    :30080
                       |
                    Service
                  port :80
                       |
               targetPort :5000
                       |
                     Pod
                10.244.0.3
                       |
                 Flask :5000
```

Kubernetes components were functioning correctly.

The original Kubernetes incident was resolved by correcting:

```yaml
targetPort: 8080
```

to:

```yaml
targetPort: 5000
```

---

# 18. Root Cause vs Secondary Environment Issue

## Primary Root Cause

```text
Service targetPort = 8080
Application port   = 5000
```

This caused the Service to forward traffic to the wrong port.

## Secondary Environment Issue

Direct Windows access to the Minikube NodePort was affected by the local Docker/WSL2 networking environment.

These were two separate issues and should not be mixed together.

---

# 19. Troubleshooting Method Used

The incident was investigated from the bottom upward.

```text
1. Infrastructure
       ↓
2. Kubernetes Node
       ↓
3. Pod
       ↓
4. Container
       ↓
5. Application
       ↓
6. Service
       ↓
7. EndpointSlice
       ↓
8. Port mapping
       ↓
9. NodePort
       ↓
10. External networking
```

The most important rule:

> Do not assume the first failing connection identifies the root cause.

Instead, isolate each layer.

---

# 20. Commands Used

### Pod

```bash
kubectl get pods -n dev -o wide
```

### Application logs

```bash
kubectl logs <pod-name> -n dev
```

### Service

```bash
kubectl get svc bank-app -n dev
```

### EndpointSlice

```bash
kubectl get endpointslice -n dev
```

### Apply Service change

```bash
kubectl apply -f service-wrong-port.yml
```

### Test Service DNS

```bash
kubectl run test-client \
  -n dev \
  --rm -it \
  --image=curlimages/curl \
  -- curl http://bank-app:80
```

### Test ClusterIP

```bash
minikube ssh -- curl -v http://10.109.150.103:80
```

### Test NodePort

```bash
minikube ssh -- curl -v http://192.168.49.2:30080
```

### Minikube Service URL

```bash
minikube service bank-app -n dev --url
```

---

# 21. Key DevOps Lessons

## Lesson 1 — Running Pod does not mean reachable application

A Pod can be:

```text
1/1 Running
```

while the application is still unreachable through a Service.

Always verify the application itself.

---

## Lesson 2 — Verify the actual listening port

Application logs showed:

```text
Flask :5000
```

The Service was configured for:

```text
targetPort: 8080
```

The application port and Service targetPort must match.

---

## Lesson 3 — EndpointSlice does not prove application health

Seeing:

```text
10.244.0.3:8080
```

does not mean port `8080` is listening inside the container.

Endpoint information must be correlated with the actual application configuration.

---

## Lesson 4 — Test from multiple network locations

A useful troubleshooting pattern is:

```text
Pod
 ↓
Service DNS
 ↓
ClusterIP
 ↓
NodePort
 ↓
External client
```

The first point where connectivity fails helps identify the faulty layer.

---

## Lesson 5 — Separate Kubernetes failures from environment failures

If:

```text
ClusterIP works
NodePort works from the node
Windows host cannot reach NodePort
```

then the problem may be outside Kubernetes.

Do not immediately change the Service configuration again.

---

# 22. Production Incident Checklist

When an application is running but unreachable through a Service:

```text
[ ] Is the Pod Running?
[ ] Is the Pod Ready?
[ ] Does the container restart?
[ ] What port is the application actually listening on?
[ ] Does the Service selector match the Pod labels?
[ ] Does the Service have endpoints?
[ ] What targetPort is configured?
[ ] Does targetPort match the application port?
[ ] Does Service DNS resolve?
[ ] Does ClusterIP work?
[ ] Does NodePort work?
[ ] Does LoadBalancer/Ingress work?
[ ] Is NetworkPolicy blocking traffic?
[ ] Is DNS working?
[ ] Is the failure inside or outside the cluster?
```

---

# 23. Interview Explanation

### Question

**A Kubernetes Pod is Running but the application is not accessible through the Service. How would you troubleshoot it?**

### Answer

I would troubleshoot from the Pod outward.

First, I would verify Pod readiness and application logs to determine which port the application is actually listening on.

Then I would verify the Service selector and EndpointSlice.

After that, I would compare the Service `targetPort` with the application's listening port.

In this incident, the Flask application was listening on port `5000`, while the Service had `targetPort: 8080`.

I changed the targetPort to `5000` and verified connectivity through the Service ClusterIP and NodePort.

Finally, I tested from outside the Minikube environment to determine whether any remaining issue was related to the Kubernetes configuration or the local networking environment.

---

# 24. Final Root Cause Statement

**The application was healthy and running on port 5000, but the Kubernetes Service was configured with `targetPort: 8080`. The Service therefore forwarded traffic to the wrong port. Updating `targetPort` to 5000 restored Service-to-Pod connectivity. Subsequent testing showed that Kubernetes networking was functioning correctly; direct Windows-to-Minikube NodePort access was a separate local Docker/WSL2 networking limitation.**

