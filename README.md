# Network Layer: Control Plane 

An implementation of the distance-vector routing protocol on a router to control routing using link costs.
Routers send and update their routing tables until all the neighboring routing tables reach convergence following the Bellman-Ford equation, and packets are then forwarded along routers using these routing tables, reflecting the below network topology:

![image](/complex.png) 

### Program Invocation

```
    python simulation_3.py
```

### Acknowledegment
Starter code provided by Prof. Mike Wittie from Montana State University.
