# Debug Filesystem

Debug FS is usually mounted under `/sys/kernel/debug` it provides more access to internal kernel data structures 
than `/proc` and `/sys` alone. It sometimes needs to be enabled explicitily during the kernel build.

## _/sys/kernel/debug/clk/clk_dump_

Should be machine readable in json format. Unfortunately there is a `,` missing before "duty_cycle".

Example: 

    {"dp_aclk": { "enable_count": 1,
                  "prepare_count": 1,
                  "protect_count": 0,
                  "rate": 100000000,
                  "accuracy": 100,
                  "phase": 0
                  "duty_cycle": 50000},
     "aux_ref_clk": { "enable_count": 0,
                      "prepare_count": 0,
                      "protect_count": 0,
                      "rate": 27000000,
                      "accuracy": 0,
                      "phase": 0
                      "duty_cycle": 50000},
