package com.coffeert.function;

import com.coffeert.model.CoffeeOrder;
import org.apache.flink.api.common.state.StateTtlConfig;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.api.common.time.Time;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Deduplicates orders by message_id using Flink keyed state.
 *
 * Each unique message_id is tracked in state with a configurable TTL.
 * Duplicates are silently dropped.
 *
 * State is checkpointed for exactly-once semantics - on recovery,
 * the state is restored and replayed messages are correctly deduplicated.
 */
public class DeduplicationFunction extends KeyedProcessFunction<String, CoffeeOrder, CoffeeOrder> {
    private static final Logger LOG = LoggerFactory.getLogger(DeduplicationFunction.class);
    private static final long serialVersionUID = 1L;

    private final int ttlMinutes;
    private transient ValueState<Boolean> seenState;

    public DeduplicationFunction(int ttlMinutes) {
        this.ttlMinutes = ttlMinutes;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        // Configure state with TTL to prevent unbounded growth
        StateTtlConfig ttlConfig = StateTtlConfig.newBuilder(Time.minutes(ttlMinutes))
                .setUpdateType(StateTtlConfig.UpdateType.OnCreateAndWrite)
                .setStateVisibility(StateTtlConfig.StateVisibility.NeverReturnExpired)
                .cleanupFullSnapshot()  // Clean expired state during checkpoints
                .build();

        ValueStateDescriptor<Boolean> descriptor = new ValueStateDescriptor<>("seen", Boolean.class);
        descriptor.enableTimeToLive(ttlConfig);

        seenState = getRuntimeContext().getState(descriptor);

        LOG.info("DeduplicationFunction initialized with TTL={} minutes", ttlMinutes);
    }

    @Override
    public void processElement(CoffeeOrder order, Context ctx, Collector<CoffeeOrder> out) throws Exception {
        // Check if we've seen this message_id before
        Boolean seen = seenState.value();

        if (seen == null) {
            // First time seeing this message_id - emit and mark as seen
            seenState.update(true);
            out.collect(order);
            LOG.debug("New order: {}", order.getMessageId());
        } else {
            // Duplicate - drop silently
            LOG.debug("Duplicate dropped: {}", order.getMessageId());
        }
    }
}
