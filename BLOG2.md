# From Bean to Byte: How My Coffee Obsession Became a Distributed Systems Problem

*A story about roasting beans, chasing real-time metrics, and accidentally becoming a backend engineer.*

---

## The First Roast

It started, as these things do, with a $40 popcorn popper and a bag of green Ethiopian Yirgacheffe beans I found on the internet.

I was just a person who liked coffee. Really liked coffee. The kind of person who could tell you the difference between a natural process and a washed process, who had opinions about bloom time, and who thought $18 for 12oz of beans was "actually pretty reasonable."

The popcorn popper worked. Too well. Within six months I had a proper drum roaster in my garage, a small Instagram following, and neighbors who either loved me or were plotting my demise (the smell of roasting coffee at 6am is polarizing).

Then someone asked if they could buy a bag.

Then ten people asked.

Then I needed a name, an LLC, and—apparently—a way to track orders.

---

## V1: The "Just Use Postgres" Era

My first coffee shop was a farmers market table and a Square reader. But I'm a developer by trade, and developers have a disease: we can't just use a spreadsheet like normal people.

"I should build a dashboard," I thought. "Something to track which drinks sell best, which roasts are moving, revenue by hour. Real-time analytics!"

Reader, it was not real-time.

**V1 was simple:**
```
Customer orders → API → PostgreSQL → Cron job (every minute) → Redis → Dashboard
```

Every minute, a little Python script would wake up, query the database, compute some aggregates, and shove them into Redis. The dashboard would poll Redis and show me pretty charts.

It worked! I could see that my Honey Process Guatemala outsold the Natural Ethiopia 3:1. I could see that Saturday morning was chaos and Tuesday afternoon was a ghost town. I felt like a real business owner with real data.

The latency to see a new order on my dashboard? About 60 seconds.

For a farmers market table selling 50 cups on a Saturday, this was fine. More than fine. It was overkill. I was checking my metrics dashboard more than I was pulling shots.

**The good times:**
- Simple to debug (it's just Postgres)
- Easy to understand (it's just a cron job)
- Cheap to run (it's just one server)

**The warning signs I ignored:**
- That one time the cron job failed and I didn't notice for 3 hours
- The dashboard showing "0 orders" while there was a line out the door
- My partner asking why I was SSHing into a server during our anniversary dinner

---

## V2: The "We're Growing!" Pivot

The farmers market led to a popup. The popup led to a lease. The lease led to... stress.

Suddenly I had a real location, real employees, and real volume. 200 orders on a Saturday. Then 400. The old Postgres setup was groaning. Not because Postgres couldn't handle it—Postgres can handle way more than 400 orders—but because my API was waiting for database writes to complete before responding to customers.

"The app feels slow," my barista said.

She was right. Every order was: receive request → write to Postgres → wait → respond. At peak times, that "wait" was becoming noticeable.

**V2 was born:**
```
Customer orders → API → Redis Streams → Worker → PostgreSQL
                   ↓
              (fast response!)
```

The idea was simple: instead of waiting for Postgres, push the order to a Redis Stream and return immediately. A background worker would consume from the stream and persist it. The API response time dropped from 15ms to 3ms.

I felt like a genius.

Redis Streams turned out to be the right choice here. Unlike Redis Pub/Sub (which I almost used), Streams actually *persist* messages. If the worker crashes, the messages wait patiently in the stream. When the worker restarts, it picks up where it left off. Consumer groups mean I can even run multiple workers for redundancy.

**The good times:**
- Blazing fast API responses
- Customers stopped complaining about the app being slow
- Messages don't get lost if the worker restarts
- I learned what "at-least-once delivery" means

**The almost-bad times:**
- Had to handle duplicate processing (same message delivered twice after a crash)
- Fixed that with idempotency keys—each order has a unique `message_id`
- `ON CONFLICT DO NOTHING` in Postgres handles the rest

**The actually-bad times:**
- Dashboard still only updates every 60 seconds (still using the cron aggregator)
- Redis Streams are great, but they're not *real-time* in the way I wanted
- Started thinking about what "real-time" actually means

The coffee shop was doing great. I wanted the dashboard to match that energy.

---

## V3: The "Okay Fine, Kafka" Admission

Every developer has a moment where they look at their growing pile of duct tape and bash scripts and think: "Maybe I should use the thing that's actually designed for this."

For me, that thing was Kafka. And later, Flink.

I resisted for months. Kafka felt like overkill. It's what Netflix uses. What LinkedIn uses. I'm a coffee shop, not a tech giant. I don't need "distributed commit logs" and "exactly-once semantics." I need to know how many lattes we sold.

But here's the thing about Kafka: it remembers.

When a message goes into Kafka, it stays there. If your consumer crashes, the messages wait. When the consumer comes back, it picks up where it left off. No more lost orders. No more 3am pages because a worker hiccuped.

**V3:**
```
Customer orders → API → Kafka → Flink → PostgreSQL
                                    ↘→ Redis (real-time!)
```

Flink is the new hotness here. Instead of a cron job that wakes up every minute to batch-compute aggregates, Flink processes each order *as it arrives*. The dashboard updates in ~100ms. Actually real-time. Not "real-time*" with an asterisk and a footnote about batch intervals.

**The good times:**
- Orders never get lost (Kafka persistence)
- Dashboard updates instantly (Flink streaming)
- I can replay history if something goes wrong
- I sleep through the night again

**The "I have become the thing I feared" times:**
- I now operate a Kafka cluster
- I now operate a Flink cluster
- I have opinions about JVM garbage collection tuning
- I've said the phrase "consumer group rebalancing" out loud

---

## The Irony

Here's the thing they don't tell you about building a real-time analytics platform for your coffee shop: at some point, you spend more time managing the analytics platform than you do making coffee.

Last Tuesday, I spent four hours debugging why my Flink job's checkpointing was failing. Four hours. I could have roasted six batches in that time. I could have dialed in the new Burundi. I could have actually *tasted* coffee instead of staring at Grafana dashboards.

My dashboard now shows me, in beautiful real-time, exactly how many milliseconds my p99 latency is. It shows me consumer lag. Partition distribution. JVM heap usage.

You know what it doesn't show me? Whether the new Gesha tastes better as a light roast or a medium roast. The dashboard can't tell me that. I have to taste it. And I haven't had time to taste anything in weeks because I'm too busy making sure the system that tracks the tasting is running.

I started roasting coffee because I loved the craft. The smell of first crack. The way a perfectly extracted shot looks like honey dripping into the cup. The face someone makes when they taste something genuinely good.

Now I have Kubernetes pods and Helm charts and a Slack channel called #coffee-rt-alerts that I check more than I check my actual espresso machine.

---

## What's Next?

I'm at a crossroads.

**Option A:** Go deeper. Add CQRS. Event sourcing. Maybe some CDC with Debezium. The dashboard could show not just current metrics but the entire history of every order, replayable, auditable, immutable. I could rebuild any view from scratch. I could—

**Option B:** Hire someone to manage this thing so I can go back to roasting.

**Option C:** Burn it all down and go back to a spreadsheet.

I'm told Option B is what "scaling a business" looks like. That at some point, the founder has to stop doing everything and start delegating. That the skills that got you from 0 to 1 aren't the skills that get you from 1 to 100.

But here's my secret: I kind of like the Flink job. I like watching the streaming DAG process 1000 orders without breaking a sweat. I like that my dashboard updates before the receipt finishes printing. I like that I built this thing.

I just also like coffee. And there's only so many hours in a day.

---

## The Lesson (If There Is One)

If you're a developer who's thinking about starting a coffee shop, or a coffee person who's thinking about building a custom analytics platform, here's my advice:

**Start with V1.** Seriously. A Postgres database and a cron job will take you further than you think. You don't need Kafka on day one. You don't need Flink. You need to sell coffee and understand your business.

**Move to V2 when V1 hurts.** When your API latency is affecting customer experience, when you need to decouple the write path, that's when you add a message queue. But understand the tradeoffs. Redis Pub/Sub is fast but lossy. Know what you're signing up for.

**Move to V3 when V2 scares you.** When lost messages keep you up at night, when you need real-time and you mean *actually real-time*, when your business depends on data integrity—that's when you bring in the big guns. Kafka. Flink. The works.

And at every step, ask yourself: *Is this making the coffee better?*

Because at the end of the day, nobody cares about your Kafka cluster. They care about the cup in their hand.

Now if you'll excuse me, I have a Flink checkpoint to investigate. And then, maybe, if there's time, I'll roast something.

---

*The author operates a small coffee roastery and spends an unreasonable amount of time thinking about message queues. The coffee is good. The distributed systems are... also good? It's complicated.*
