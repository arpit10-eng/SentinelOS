#include <stdio.h>
#include <dirent.h>
#include <ctype.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

#define MAX_PROCESSES 2048

struct ProcessInfo
{
    int pid;
    int ppid;
    char name[100];
    char state;
    long memory;

    long cpu_ticks;

    long read_bytes;
    long write_bytes;

    long read_rate;
    long write_rate;

    double cpu_usage;
};


/* =========================================================
   Get CPU ticks used by one process
   ========================================================= */

long get_process_cpu_ticks(const char *pid)
{
    char path[512];
    char line[2048];

    snprintf(
        path,
        sizeof(path),
        "/proc/%s/stat",
        pid
    );

    FILE *file = fopen(path, "r");

    if (file == NULL)
    {
        return -1;
    }

    if (fgets(line, sizeof(line), file) == NULL)
    {
        fclose(file);
        return -1;
    }

    fclose(file);

    char *closing_bracket = strrchr(line, ')');

    if (closing_bracket == NULL)
    {
        return -1;
    }

    char *data = closing_bracket + 2;

    char *token = strtok(data, " ");

    long utime = 0;
    long stime = 0;

    int field = 3;

    while (token != NULL)
    {
        if (field == 14)
        {
            utime = atol(token);
        }
        else if (field == 15)
        {
            stime = atol(token);
            break;
        }

        token = strtok(NULL, " ");
        field++;
    }

    return utime + stime;
}


/* =========================================================
   Get total CPU ticks of the system
   ========================================================= */

long get_total_cpu_ticks()
{
    FILE *file = fopen("/proc/stat", "r");

    if (file == NULL)
    {
        return -1;
    }

    char line[1024];

    if (fgets(line, sizeof(line), file) == NULL)
    {
        fclose(file);
        return -1;
    }

    fclose(file);

    unsigned long long user;
    unsigned long long nice;
    unsigned long long system;
    unsigned long long idle;
    unsigned long long iowait;
    unsigned long long irq;
    unsigned long long softirq;
    unsigned long long steal;
    unsigned long long guest;
    unsigned long long guest_nice;

    int result = sscanf(
        line,
        "cpu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu",
        &user,
        &nice,
        &system,
        &idle,
        &iowait,
        &irq,
        &softirq,
        &steal,
        &guest,
        &guest_nice
    );

    if (result != 10)
    {
        return -1;
    }

    unsigned long long total =
        user +
        nice +
        system +
        idle +
        iowait +
        irq +
        softirq +
        steal +
        guest +
        guest_nice;

    return (long)total;
}


/* =========================================================
   Get disk I/O information of a process
   ========================================================= */

void get_process_io(
    const char *pid,
    long *read_bytes,
    long *write_bytes)
{
    char path[512];
    char line[256];

    *read_bytes = 0;
    *write_bytes = 0;

    snprintf(
        path,
        sizeof(path),
        "/proc/%s/io",
        pid
    );

    FILE *file = fopen(path, "r");

    if (file == NULL)
    {
        return;
    }

    while (fgets(line, sizeof(line), file) != NULL)
    {
        if (strncmp(line, "read_bytes:", 11) == 0)
        {
            sscanf(
                line + 11,
                "%ld",
                read_bytes
            );
        }
        else if (strncmp(line, "write_bytes:", 12) == 0)
        {
            sscanf(
                line + 12,
                "%ld",
                write_bytes
            );
        }
    }

    fclose(file);
}


/* =========================================================
   Find a process from the previous snapshot
   ========================================================= */

int find_previous_process(
    struct ProcessInfo previous[],
    int previous_count,
    int pid)
{
    for (int i = 0; i < previous_count; i++)
    {
        if (previous[i].pid == pid)
        {
            return i;
        }
    }

    return -1;
}


/* =========================================================
   Check whether a parent process currently exists
   ========================================================= */

int parent_exists(
    struct ProcessInfo processes[],
    int process_count,
    int ppid)
{
    /*
       PPID 0 means there is no normal parent process.
       This can happen for special kernel/system processes.
    */

    if (ppid == 0)
    {
        return 0;
    }

    for (int i = 0; i < process_count; i++)
    {
        if (processes[i].pid == ppid)
        {
            return 1;
        }
    }

    return 0;
}


/* =========================================================
   Collect process information
   ========================================================= */

int collect_processes(
    struct ProcessInfo processes[],
    int max_processes)
{
    DIR *proc_dir;
    struct dirent *entry;

    proc_dir = opendir("/proc");

    if (proc_dir == NULL)
    {
        printf("Unable to open /proc\n");
        return -1;
    }

    int count = 0;

    while ((entry = readdir(proc_dir)) != NULL)
    {
        /*
           Only directories whose names start with a digit
           are considered process directories.
        */

        if (!isdigit((unsigned char)entry->d_name[0]))
        {
            continue;
        }

        if (count >= max_processes)
        {
            break;
        }

        char path[512];
        char line[256];

        struct ProcessInfo *process =
            &processes[count];

        /*
           Initialize process information.
        */

        process->pid = atoi(entry->d_name);

        process->ppid = 0;

        process->name[0] = '\0';

        process->state = '?';

        process->memory = 0;

        process->cpu_ticks = -1;

        process->read_bytes = 0;
        process->write_bytes = 0;

        process->read_rate = 0;
        process->write_rate = 0;

        process->cpu_usage = 0.0;


        /* -----------------------------------------------
           Read /proc/PID/status
           ----------------------------------------------- */

        snprintf(
            path,
            sizeof(path),
            "/proc/%s/status",
            entry->d_name
        );

        FILE *file = fopen(path, "r");

        if (file == NULL)
        {
            continue;
        }

        while (fgets(line, sizeof(line), file) != NULL)
        {
            /*
               Process name
            */

            if (strncmp(line, "Name:", 5) == 0)
            {
                sscanf(
                    line + 5,
                    "%99[^\n]",
                    process->name
                );

                char *start = process->name;

                while (*start == ' ' ||
                       *start == '\t')
                {
                    start++;
                }

                memmove(
                    process->name,
                    start,
                    strlen(start) + 1
                );
            }

            /*
               Process state
            */

            else if (strncmp(line, "State:", 6) == 0)
            {
                sscanf(
                    line,
                    "State:\t%c",
                    &process->state
                );
            }

            /*
               Parent Process ID
            */

            else if (strncmp(line, "PPid:", 5) == 0)
            {
                sscanf(
                    line,
                    "PPid:\t%d",
                    &process->ppid
                );
            }

            /*
               Resident memory
            */

            else if (strncmp(line, "VmRSS:", 6) == 0)
            {
                sscanf(
                    line,
                    "VmRSS:\t%ld",
                    &process->memory
                );
            }
        }

        fclose(file);


        /* -----------------------------------------------
           CPU information
           ----------------------------------------------- */

        process->cpu_ticks =
            get_process_cpu_ticks(
                entry->d_name
            );

        if (process->cpu_ticks < 0)
        {
            continue;
        }


        /* -----------------------------------------------
           Disk I/O information
           ----------------------------------------------- */

        get_process_io(
            entry->d_name,
            &process->read_bytes,
            &process->write_bytes
        );


        count++;
    }

    closedir(proc_dir);

    return count;
}


/* =========================================================
   Main
   ========================================================= */

int main()
{
    struct ProcessInfo previous[MAX_PROCESSES];

    struct ProcessInfo current[MAX_PROCESSES];


    /* -----------------------------------------------------
       Get number of logical CPUs
       ----------------------------------------------------- */

    long cpu_count =
        sysconf(_SC_NPROCESSORS_ONLN);

    if (cpu_count < 1)
    {
        cpu_count = 1;
    }


    /* -----------------------------------------------------
       First process snapshot
       ----------------------------------------------------- */

    int previous_count =
        collect_processes(
            previous,
            MAX_PROCESSES
        );


    /* -----------------------------------------------------
       First total CPU snapshot
       ----------------------------------------------------- */

    long total_previous =
        get_total_cpu_ticks();


    if (previous_count < 0 ||
        total_previous < 0)
    {
        printf(
            "Unable to collect initial system information.\n"
        );

        return 1;
    }


    printf(
        "SentinelOS monitor starting...\n"
    );

    printf(
        "Logical CPUs: %ld\n",
        cpu_count
    );

    printf(
        "Calculating CPU and I/O rates...\n"
    );


    /*
       Wait so that we can compare two snapshots.
    */

    sleep(2);


    /* =====================================================
       Continuous monitoring
       ===================================================== */

    while (1)
    {
        /*
           Collect current process information.
        */

        int current_count =
            collect_processes(
                current,
                MAX_PROCESSES
            );


        /*
           Collect current total CPU information.
        */

        long total_current =
            get_total_cpu_ticks();


        if (current_count < 0 ||
            total_current < 0)
        {
            sleep(2);
            continue;
        }


        /*
           Difference in total CPU ticks.
        */

        long total_difference =
            total_current -
            total_previous;


        /*
           Clear terminal screen.
        */

        printf("\033[2J\033[H");


        /* -------------------------------------------------
           Header
           ------------------------------------------------- */

        printf(
            "============================================================================================================\n"
        );

        printf(
            "                                      SentinelOS Process Monitor\n"
        );

        printf(
            "============================================================================================================\n"
        );

        printf(
            "Logical CPUs: %ld\n",
            cpu_count
        );

        printf(
            "Refreshing every 2 seconds...\n"
        );

        printf(
            "Process relationship is based on PID and PPID.\n"
        );

        printf(
            "Press Ctrl+C to stop.\n\n"
        );


        /* -------------------------------------------------
           Table header
           ------------------------------------------------- */

        printf(
            "%-8s %-8s %-18s %-7s %-12s %-12s %-14s %-14s %s\n",
            "PID",
            "PPID",
            "NAME",
            "STATE",
            "MEMORY(kB)",
            "PARENT",
            "READ/s",
            "WRITE/s",
            "CPU"
        );

        printf(
            "------------------------------------------------------------------------------------------------------------\n"
        );


        /* =================================================
           Process information
           ================================================= */

        for (int i = 0;
             i < current_count;
             i++)
        {
            /*
               Find the same process in the previous
               snapshot.
            */

            int previous_index =
                find_previous_process(
                    previous,
                    previous_count,
                    current[i].pid
                );


            /*
               Check whether this process's parent
               currently exists.
            */

            int parent_status =
                parent_exists(
                    current,
                    current_count,
                    current[i].ppid
                );


            /* -------------------------------------------------
               Calculate CPU and I/O rates
               ------------------------------------------------- */

            if (previous_index != -1 &&
                total_difference > 0)
            {
                /*
                   CPU difference
                */

                long process_difference =
                    current[i].cpu_ticks -
                    previous[previous_index].cpu_ticks;


                if (process_difference >= 0)
                {
                    current[i].cpu_usage =
                        (
                            (double)process_difference /
                            (double)total_difference
                        )
                        * cpu_count
                        * 100.0;
                }
                else
                {
                    current[i].cpu_usage = 0.0;
                }


                /*
                   READ bytes per second
                */

                long read_difference =
                    current[i].read_bytes -
                    previous[previous_index].read_bytes;


                if (read_difference >= 0)
                {
                    current[i].read_rate =
                        read_difference / 2;
                }
                else
                {
                    current[i].read_rate = 0;
                }


                /*
                   WRITE bytes per second
                */

                long write_difference =
                    current[i].write_bytes -
                    previous[previous_index].write_bytes;


                if (write_difference >= 0)
                {
                    current[i].write_rate =
                        write_difference / 2;
                }
                else
                {
                    current[i].write_rate = 0;
                }


                /* ---------------------------------------------
                   Print complete process information
                   --------------------------------------------- */

                printf(
                    "%-8d %-8d %-18s %-7c %-12ld %-12s %-14ld %-14ld %.2f%%\n",
                    current[i].pid,
                    current[i].ppid,
                    current[i].name,
                    current[i].state,
                    current[i].memory,
                    parent_status ? "EXISTS" : "NONE",
                    current[i].read_rate,
                    current[i].write_rate,
                    current[i].cpu_usage
                );
            }


            /* -------------------------------------------------
               New process / first observation
               ------------------------------------------------- */

            else
            {
                printf(
                    "%-8d %-8d %-18s %-7c %-12ld %-12s %-14s %-14s ---\n",
                    current[i].pid,
                    current[i].ppid,
                    current[i].name,
                    current[i].state,
                    current[i].memory,
                    parent_status ? "EXISTS" : "NONE",
                    "---",
                    "---"
                );
            }
        }


        /* =================================================
           Save current snapshot for next comparison
           ================================================= */

        memcpy(
            previous,
            current,
            sizeof(struct ProcessInfo) *
            current_count
        );


        previous_count = current_count;

        total_previous = total_current;


        /*
           Wait two seconds before next snapshot.
        */

        sleep(2);
    }


    return 0;
}