package com.coffeert.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.io.Serializable;
import java.math.BigDecimal;
import java.time.Instant;

/**
 * POJO representing a coffee order from Kafka.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CoffeeOrder implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("message_id")
    private String messageId;

    @JsonProperty("drink")
    private String drink;

    @JsonProperty("store")
    private String store;

    @JsonProperty("price")
    private BigDecimal price;

    @JsonProperty("timestamp")
    private String timestamp;

    @JsonProperty("version")
    private String version;

    public CoffeeOrder() {}

    public CoffeeOrder(String messageId, String drink, String store, BigDecimal price, String timestamp, String version) {
        this.messageId = messageId;
        this.drink = drink;
        this.store = store;
        this.price = price;
        this.timestamp = timestamp;
        this.version = version;
    }

    public String getMessageId() {
        return messageId;
    }

    public void setMessageId(String messageId) {
        this.messageId = messageId;
    }

    public String getDrink() {
        return drink;
    }

    public void setDrink(String drink) {
        this.drink = drink;
    }

    public String getStore() {
        return store;
    }

    public void setStore(String store) {
        this.store = store;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public void setPrice(BigDecimal price) {
        this.price = price;
    }

    public String getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(String timestamp) {
        this.timestamp = timestamp;
    }

    public String getVersion() {
        return version;
    }

    public void setVersion(String version) {
        this.version = version;
    }

    public Instant getTimestampAsInstant() {
        if (timestamp == null) {
            return Instant.now();
        }
        try {
            return Instant.parse(timestamp);
        } catch (Exception e) {
            return Instant.now();
        }
    }

    @Override
    public String toString() {
        return "CoffeeOrder{" +
                "messageId='" + messageId + '\'' +
                ", drink='" + drink + '\'' +
                ", store='" + store + '\'' +
                ", price=" + price +
                ", timestamp='" + timestamp + '\'' +
                ", version='" + version + '\'' +
                '}';
    }
}
